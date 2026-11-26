from datetime import datetime

import httpx2
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from api.ingestion.facilities.client import FacilitySourceError, fetch_rows
from api.ingestion.facilities.normalize import SOURCES, unique
from api.ingestion.facilities.store import LoadResult, fail_job, finish_job, start_job


def load_source(
    engine: Engine, source_id: str, now: datetime, *, http_client: httpx2.Client | None = None,
) -> LoadResult:
    source = SOURCES[source_id]
    job_id = start_job(engine, source, now)
    try:
        rows = fetch_rows(source.service, http_client)
    except FacilitySourceError as error:
        fail_job(engine, job_id, error.code, now)
        raise RuntimeError(f"{source.name} 목록 수집에 실패했습니다({error.code}).") from None
    items, _ = unique(source.normalize(rows))
    try:
        return finish_job(engine, job_id, source, items, len(rows), now)
    except SQLAlchemyError:
        fail_job(engine, job_id, "DB_ERROR", now)
        raise RuntimeError(f"{source.name} DB 저장에 실패했습니다.") from None
