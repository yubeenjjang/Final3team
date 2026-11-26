"""사용자 요청과 내부 작업에 별도 PostgreSQL 연결 풀을 만듭니다."""

from typing import TYPE_CHECKING

from ..config import DBRole, DBSettings, load_db_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine
    from sqlalchemy.ext.asyncio import AsyncEngine


def _connection_url(settings: DBSettings, role: DBRole):
    # URL.create가 비밀번호의 특수문자를 안전하게 처리합니다.
    from sqlalchemy.engine import URL

    username, password = settings.credentials(role)
    return URL.create(
        "postgresql+psycopg",
        username=username,
        password=password,
        host=settings.host,
        port=settings.port,
        database=settings.name,
    )


def _reset_on_return(engine: "Engine | AsyncEngine") -> None:
    """연결 풀 반납 때 커밋된 세션 설정까지 지웁니다."""
    from sqlalchemy import event

    target = engine.sync_engine if hasattr(engine, "sync_engine") else engine

    @event.listens_for(target, "reset")
    def reset_session(dbapi_connection, connection_record, reset_state) -> None:
        if reset_state.terminate_only:
            return
        dbapi_connection.rollback()
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("RESET ALL")
        finally:
            cursor.close()
        # RESET ALL도 트랜잭션 안에서 실행되므로 확정해야 유지됩니다.
        dbapi_connection.commit()


def create_user_engine(settings: DBSettings | None = None) -> "AsyncEngine":
    """FastAPI 사용자 요청용 비동기 풀(RLS 적용 계정)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    settings = settings or load_db_settings()
    engine = create_async_engine(
        _connection_url(settings, "user"),
        pool_pre_ping=True,
        pool_reset_on_return=None,
    )
    _reset_on_return(engine)
    return engine


def create_service_engine(settings: DBSettings | None = None) -> "Engine":
    """수집·감지·Celery 작업용 동기 풀(RLS 우회 계정)."""
    from sqlalchemy import create_engine

    settings = settings or load_db_settings()
    engine = create_engine(
        _connection_url(settings, "service"),
        pool_pre_ping=True,
        pool_reset_on_return=None,
    )
    _reset_on_return(engine)
    return engine
