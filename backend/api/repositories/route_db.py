"""귀가 저장소용 서비스 세션. 공통 shared/db 병합 뒤 교체한다."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, event
from sqlalchemy.orm import Session

from api.ingestion.db import create_ingestion_engine


@lru_cache(maxsize=1)
def _service_engine() -> Engine:
    engine = create_ingestion_engine(pool_pre_ping=True, pool_reset_on_return=None)

    @event.listens_for(engine, "reset")
    def reset_session(connection, _record, state) -> None:
        if state.terminate_only:
            return
        connection.rollback()
        with connection.cursor() as cursor:
            cursor.execute("RESET ALL")
        connection.commit()

    return engine


@contextmanager
def service_db_session() -> Iterator[Session]:
    with Session(_service_engine()) as session, session.begin():
        yield session
