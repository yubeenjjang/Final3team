import argparse
import json
import sys
from collections import Counter
from collections.abc import Callable, Mapping
from contextlib import ExitStack
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx2
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from api.ingestion.db import IngestionDBError
from api.ingestion.festivals.normalize import (
    KST, FestivalRecord, normalize_festival, source_item_id, source_version,
)
from api.ingestion.festivals.store import ErrorEntry, FestivalStore, JobResult, ListingScope, StoredFestival
from api.jobs.locks import FESTIVALS
from api.providers.tourapi import TourApiClient, TourApiError
from shared.db.session import service_db_session

DETAIL_CALL_LIMIT = 900
DETAIL_ENDPOINTS = ("detailCommon2", "detailIntro2")


@dataclass(frozen=True)
class CollectionOptions:
    since: date
    until: date | None = None
    limit: int | None = None
    out: Path | None = None
    no_detail: bool = False
    db: bool = False


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
        content_id = source_item_id(item)
        previous = stored.get(content_id) if stored is not None else None
        changed = should_fetch_details(source_version(item), previous)
        quota_reached = any(
            client.calls.get(endpoint, 0) >= DETAIL_CALL_LIMIT for endpoint in DETAIL_ENDPOINTS
        )
        fetch_details = changed and not no_detail and not quota_reached
        common, intro = None, None
        if fetch_details:
            common, intro = _fetch_details(client, content_id, errors)
        elif changed and quota_reached and not no_detail:
            issues["detail_skipped_quota"] += 1
        record = normalize_festival(
            item, common, intro, today=today, details_requested=fetch_details,
        )
        if stored is not None and (common is None or intro is None):
            record = _reuse_details(record, previous, changed)
        records.append(record)
        issues.update(record.issues)
    return records


def _record_json(record: FestivalRecord, client: TourApiClient) -> str:
    data = {
        name: client.redact(value) if isinstance(value, str) else value
        for name, value in asdict(record).items()
        if name != "listing_updated_at"
    }
    return json.dumps(data, ensure_ascii=False, default=_isoformat)


def _isoformat(value: date) -> str:
    return value.isoformat()


def _db_error(errors: list[ErrorEntry], stage: str, *, report_errors: bool) -> None:
    errors.append({"content_id": None, "stage": stage, "code": "DB_ERROR"})
    if report_errors:
        print("축제 DB 작업에 실패했습니다. DB 설정과 연결을 확인해 주세요.", file=sys.stderr)


def _finish_db_job(
    store: FestivalStore,
    job_id: str,
    records: list[FestivalRecord],
    errors: list[ErrorEntry],
    status: int,
    redact: Callable[[str], str],
    scope: ListingScope | None,
    *,
    report_errors: bool,
) -> tuple[JobResult | None, int]:
    try:
        return store.finish_job(
            job_id, records, errors, failed=bool(status), redact=redact, scope=scope,
        ), status
    except SQLAlchemyError:
        _db_error(errors, "db_finish", report_errors=report_errors)
    try:
        return store.finish_job(job_id, records, errors, failed=True), 1
    except SQLAlchemyError:
        return None, 1


def _collect(
    args: CollectionOptions, http_client: httpx2.Client | None, *, locked_engine: Engine | None = None,
) -> tuple[int, JobResult | None]:
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
    report_errors = args.out is not None
    with ExitStack() as stack:
        output = None
        try:
            if args.db:
                engine = locked_engine
                if engine is None:
                    try:
                        lock = stack.enter_context(service_db_session())
                    except ValueError:
                        raise IngestionDBError("공통 DB 접속 설정을 확인해 주세요.") from None
                    if not lock.scalar(FESTIVALS):
                        print("축제 수집 작업이 이미 실행 중입니다.", file=sys.stderr)
                        return 3, None
                    # Store operations keep their own commits while the lock transaction stays open.
                    engine = lock.get_bind()
                store = FestivalStore(engine)
            if args.out is not None:
                args.out.mkdir(parents=True, exist_ok=True)
                output = stack.enter_context((args.out / "festivals.jsonl").open("w", encoding="utf-8"))
            if store is not None:
                job_id = store.start_job(started_at)
            with TourApiClient(http_client) as client:
                redact = client.redact
                calls = client.calls
                items = client.search_festivals(args.since, args.until)[: args.limit]
                stored = None
                if store is not None:
                    stored = store.load({source_item_id(item) for item in items} - {""})
                records = _normalize_items(
                    client, items, started_at.date(), args.no_detail, issues, errors, stored,
                )
                if output is not None:
                    for record in records:
                        output.write(_record_json(record, client) + "\n")
        except TourApiError as error:
            errors.append({"content_id": None, "stage": "searchFestival2", "code": error.code})
            if report_errors:
                print(f"축제 목록을 수집하지 못했습니다 ({error.code}).", file=sys.stderr)
            status = 1
        except (IngestionDBError, SQLAlchemyError):
            _db_error(errors, "db_load" if job_id else "db_start", report_errors=report_errors)
            status = 1
        if store is not None and job_id is not None:
            scope = None
            if not status and not errors and args.limit is None and not issues["detail_skipped_quota"]:
                scope = ListingScope(args.since, args.until)
            job, status = _finish_db_job(
                store, job_id, records, errors, status, redact, scope, report_errors=report_errors,
            )

    if args.out is None:
        return status, job
    if output is None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "festivals.jsonl").write_text("", encoding="utf-8")
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
    return status, job


def collect_to_db(since: date, *, locked_engine: Engine) -> JobResult:
    """정기 실행기가 FESTIVALS 잠금을 보유한 상태에서 파일 출력 없이 수집한다."""
    status, job = _collect(CollectionOptions(since=since, db=True), None, locked_engine=locked_engine)
    if status or job is None or job.status != "success":
        raise RuntimeError("축제 DB 수집을 완료하지 못했습니다.")
    return job


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
    status, _ = _collect(CollectionOptions(**vars(args)), http_client)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
