import argparse
import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx2

from api.ingestion.festivals.normalize import KST, FestivalRecord, normalize_festival
from api.providers.tourapi import TourApiClient, TourApiError

DETAIL_CALL_LIMIT = 900
DETAIL_ENDPOINTS = ("detailCommon2", "detailIntro2")


def _fetch_details(
    client: TourApiClient, content_id: str, errors: list[dict[str, str | None]]
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


def _normalize_items(
    client: TourApiClient,
    items: list[dict[str, Any]],
    today: date,
    no_detail: bool,
    issues: Counter[str],
    errors: list[dict[str, str | None]],
) -> list[FestivalRecord]:
    records: list[FestivalRecord] = []
    for item in items:
        quota_reached = any(
            client.calls.get(endpoint, 0) >= DETAIL_CALL_LIMIT for endpoint in DETAIL_ENDPOINTS
        )
        fetch_details = not no_detail and not quota_reached
        common, intro = None, None
        if fetch_details:
            content_id = str(item.get("contentid") or "")
            common, intro = _fetch_details(client, content_id, errors)
        elif quota_reached and not no_detail:
            issues["detail_skipped_quota"] += 1
        record = normalize_festival(item, common, intro, today=today, details_requested=fetch_details)
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


def _collect(args: argparse.Namespace, http_client: httpx2.Client | None) -> int:
    started_at = datetime.now(KST)
    errors: list[dict[str, str | None]] = []
    issues: Counter[str] = Counter()
    calls: dict[str, int] = {}
    records: list[FestivalRecord] = []
    status = 0
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "festivals.jsonl").open("w", encoding="utf-8") as output:
        try:
            with TourApiClient(http_client) as client:
                calls = client.calls
                items = client.search_festivals(args.since, args.until)
                records = _normalize_items(
                    client, items[: args.limit], started_at.date(), args.no_detail, issues, errors
                )
                for record in records:
                    output.write(_record_json(record, client) + "\n")
        except TourApiError as error:
            errors.append({"content_id": None, "stage": "searchFestival2", "code": error.code})
            print(f"축제 목록을 수집하지 못했습니다 ({error.code}).", file=sys.stderr)
            status = 1

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
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 0:
        parser.error("--limit은 0 이상이어야 합니다.")
    if args.until is not None and args.until < args.since:
        parser.error("--until은 --since보다 빠를 수 없습니다.")
    return _collect(args, http_client)


if __name__ == "__main__":
    raise SystemExit(main())
