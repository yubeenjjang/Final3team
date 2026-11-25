import os
from datetime import datetime

import httpx2
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from api.ingestion.festivals.store import ErrorEntry, JobResult
from api.ingestion.seoul_culture.client import SERVICE, SeoulCultureError, fetch_events
from api.ingestion.seoul_culture.normalize import normalize_event
from api.ingestion.seoul_culture.store import SeoulCultureStore


def enabled() -> bool:
    return os.environ.get("SEOUL_CULTURE_ENABLED", "false").strip().lower() == "true"


def _error(code: str, content_id: str | None = None) -> ErrorEntry:
    return {"content_id": content_id, "stage": SERVICE, "code": code}


def collect_to_db(
    started_at: datetime, *, locked_engine: Engine, http_client: httpx2.Client | None = None,
) -> JobResult:
    """정기 실행기가 축제 수집 잠금을 보유한 상태에서 서울시 축제를 보강한다."""
    store = SeoulCultureStore(locked_engine)
    job_id = store.start_job(started_at)
    try:
        rows = fetch_events(http_client)
    except SeoulCultureError as error:
        store.finish_job(job_id, [], 0, [_error(error.code)], failed=True)
        raise RuntimeError("서울시 문화행사 목록 수집에 실패했습니다.") from None

    events = []
    errors = []
    for row in rows:
        event, content_id, code = normalize_event(row, started_at.date())
        if code:
            errors.append(_error(code, content_id))
        if event is not None:
            events.append(event)

    # 한 목록 안에 같은 번호로 서로 다른 축제 정보가 오면 어느 쪽도 채택하지 않는다.
    versions: dict[str, set[str]] = {}
    for event in events:
        versions.setdefault(event.source_item_id, set()).add(event.raw_checksum)
    conflicting_ids = {item_id for item_id, checksums in versions.items() if len(checksums) > 1}
    errors.extend(_error("CONFLICTING_SOURCE_ID", item_id) for item_id in sorted(conflicting_ids))
    unique = {event.source_item_id: event for event in events if event.source_item_id not in conflicting_ids}
    # 같은 원본의 반복 노출은 정상 행으로 한 번만 처리하고 나머지는 제외 건수에 포함한다.
    try:
        return store.finish_job(job_id, list(unique.values()), len(rows), errors)
    except SQLAlchemyError:
        store.finish_job(job_id, [], len(rows), [*errors, _error("DB_ERROR")], failed=True)
        raise RuntimeError("서울시 문화행사 DB 저장에 실패했습니다.") from None
