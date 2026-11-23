import argparse
import json
import sys
from collections import Counter
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from dataclasses import asdict, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx2
from sqlalchemy.exc import SQLAlchemyError

from api.ingestion.db import IngestionDBError, create_ingestion_engine
from api.ingestion.festivals.normalize import KST, FestivalRecord, normalize_festival
from api.ingestion.festivals.store import ErrorEntry, FestivalStore, JobResult, ListingScope, StoredFestival
from api.providers.tourapi import TourApiClient, TourApiError

DETAIL_CALL_LIMIT = 900
DETAIL_ENDPOINTS = ("detailCommon2", "detailIntro2")


def _fetch_details(
    client: TourApiClient, content_id: str, errors: list[ErrorEntry]
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    def fetch(
        endpoint: str, get_detail: Callable[..., dict[str, Any]]
    ) -> dict[str, Any] | None:
        try:
            return get_detail(content_id, call_limit=DETAIL_CALL_LIMIT)
        except TourApiError as error:
            errors.append(
                {"content_id": client.redact(content_id), "stage": endpoint, "code": error.code}
            )
            return None

    return fetch("detailCommon2", client.get_common), fetch("detailIntro2", client.get_intro)


def should_fetch_details(version: datetime | None, previous: StoredFestival | None) -> bool:
    if previous is None:
        return True
    return version is not None and (
        previous.source_updated_at is None or version > previous.source_updated_at
    )


def _reuse_details(
    record: FestivalRecord, previous: StoredFestival | None, changed: bool
) -> FestivalRecord:
    # 상세 수집을 다음 실행에서 재시도할 수 있도록 이전 상세의 수정 시각을 유지한다.
    if previous is None:
        return replace(record, source_updated_at=None)
    return replace(
        record, **previous.details, source_updated_at=previous.source_updated_at,
        raw_checksum=record.raw_checksum if changed else previous.raw_checksum,
    )


def _normalize_items(
    client: TourApiClient,
    items: list[dict[str, Any]],
    today: date,
    no_detail: bool,
    issues: Counter[str],
    errors: list[ErrorEntry],
    stored: Mapping[str, StoredFestival] | None = None,
) -> list[FestivalRecord]:
    records: list[FestivalRecord] = []
    for item in items:
        record = None
        previous = None
        changed = True
        if stored is not None:
            record = normalize_festival(item, today=today, details_requested=False)
            previous = stored.get(record.source_item_id)
            changed = should_fetch_details(record.source_updated_at, previous)
        quota_reached = any(
            client.calls.get(endpoint, 0) >= DETAIL_CALL_LIMIT for endpoint in DETAIL_ENDPOINTS
        )
        fetch_details = changed and not no_detail and not quota_reached
        common, intro = None, None
        if fetch_details:
            content_id = record.source_item_id if record is not None else str(item.get("contentid") or "")
            common, intro = _fetch_details(client, content_id, errors)
        elif changed and quota_reached and not no_detail:
            issues["detail_skipped_quota"] += 1
        if record is None or fetch_details:
            record = normalize_festival(item, common, intro, today=today, details_requested=fetch_details)
        if stored is not None and (common is None or intro is None):
            record = _reuse_details(record, previous, changed)
        records.append(record)
        issues.update(record.issues)
    return records


def _record_json(record: FestivalRecord, client: TourApiClient) -> str:
    data = {
        name: client.redact(value) if isinstance(value, str) else value
        for name, value in asdict(record).items()
    }
    return json.dumps(data, ensure_ascii=False, default=_isoformat)


def _isoformat(value: date) -> str:
    return value.isoformat()


def _db_error(errors: list[ErrorEntry], stage: str) -> None:
    errors.append({"content_id": None, "stage": stage, "code": "DB_ERROR"})
    print("축제 DB 작업에 실패했습니다. DB 설정과 연결을 확인해 주세요.", file=sys.stderr)


def _finish_db_job(
    store: FestivalStore,
    job_id: str,
    records: list[FestivalRecord],
    errors: list[ErrorEntry],
    status: int,
    redact: Callable[[str], str],
    scope: ListingScope | None,
) -> tuple[JobResult | None, int]:
    try:
        return store.finish_job(
            job_id, records, errors, failed=bool(status), redact=redact, scope=scope,
        ), status
    except SQLAlchemyError:
        _db_error(errors, "db_finish")
    try:
        return store.finish_job(job_id, records, errors, failed=True), 1
    except SQLAlchemyError:
        return None, 1


def _collect(args: argparse.Namespace, http_client: httpx2.Client | None) -> int:
    started_at = datetime.now(KST)
    errors: list[ErrorEntry] = []
    issues: Counter[str] = Counter()
    calls: dict[str, int] = {}
    records: list[FestivalRecord] = []
    status = 0
    store = None
    job_id = None
    job = None
    redact: Callable[[str], str] = str
    args.out.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        output = stack.enter_context((args.out / "festivals.jsonl").open("w", encoding="utf-8"))
        try:
            if args.db:
                engine = create_ingestion_engine()
                stack.callback(engine.dispose)
                store = FestivalStore(engine)
                job_id = store.start_job(started_at)
            with TourApiClient(http_client) as client:
                redact = client.redact
                calls = client.calls
                items = client.search_festivals(args.since, args.until)[: args.limit]
                stored = None
                if store is not None:
                    stored = store.load({str(item["contentid"]).strip() for item in items
                                         if item.get("contentid") is not None})
                records = _normalize_items(
                    client, items, started_at.date(), args.no_detail, issues, errors, stored
                )
                for record in records:
                    output.write(_record_json(record, client) + "\n")
        except TourApiError as error:
            errors.append({"content_id": None, "stage": "searchFestival2", "code": error.code})
            print(f"축제 목록을 수집하지 못했습니다 ({error.code}).", file=sys.stderr)
            status = 1
        except (IngestionDBError, SQLAlchemyError):
            _db_error(errors, "db_load" if job_id else "db_start")
            status = 1
        if store is not None and job_id is not None:
            scope = None
            if not status and not errors and args.limit is None and not issues["detail_skipped_quota"]:
                scope = ListingScope(args.since, args.until)
            job, status = _finish_db_job(store, job_id, records, errors, status, redact, scope)

    publishable = sum(record.publishable for record in records)
    report = {
        "started_at": started_at,
        "ended_at": datetime.now(KST),
        "since": args.since,
        "until": args.until,
        "scanned": len(records),
        "publishable": publishable,
        "pending": len(records) - publishable,
        "issues": dict(issues),
        "calls": calls,
        "errors": errors,
    }
    if args.db:
        report["db"] = asdict(job) if job is not None else None
    (args.out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=_isoformat) + "\n", encoding="utf-8"
    )
    return status


def _parse_date(value: str) -> date:
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("날짜를 YYYY-MM-DD 형식으로 입력해 주세요.") from None
    if result.isoformat() != value:
        raise argparse.ArgumentTypeError("날짜를 YYYY-MM-DD 형식으로 입력해 주세요.")
    return result


def main(argv: list[str] | None = None, *, http_client: httpx2.Client | None = None) -> int:
    parser = argparse.ArgumentParser(description="TourAPI 축제 목록과 상세를 수집합니다.")
    parser.add_argument("--since", required=True, type=_parse_date)
    parser.add_argument("--until", type=_parse_date)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--no-detail", action="store_true")
    parser.add_argument("--db", action="store_true", help="수집한 축제를 DB에도 저장합니다.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        parser.error("--limit은 0 이상이어야 합니다.")
    if args.until is not None and args.until < args.since:
        parser.error("--until은 --since보다 빠를 수 없습니다.")
    return _collect(args, http_client)


if __name__ == "__main__":
    raise SystemExit(main())
