"""요청마다 트랜잭션을 열고 닫는 공통 DB 세션."""

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session, sessionmaker

from .connection import create_service_engine, create_user_engine


@lru_cache(maxsize=1)
def _user_engine() -> AsyncEngine:
    return create_user_engine()


@lru_cache(maxsize=1)
def _service_engine() -> Engine:
    return create_service_engine()


@asynccontextmanager
async def user_db_session(user_id: UUID | None = None) -> AsyncIterator[AsyncSession]:
    """검증된 JWT의 sub만 전달합니다. None이면 비회원 요청입니다."""
    maker = async_sessionmaker(_user_engine(), expire_on_commit=False)
    async with maker() as session:
        # begin()은 정상 종료 시 커밋하고 예외가 나면 롤백합니다.
        async with session.begin():
            if user_id is not None:
                # 세 번째 인자 true: 이 트랜잭션에만 사용자 ID를 설정합니다.
                await session.execute(
                    text("SELECT set_config('app.user_id', :user_id, true)"),
                    {"user_id": str(user_id)},
                )
            yield session


async def get_db() -> AsyncIterator[AsyncSession]:
    """비회원 FastAPI 요청에 쓰는 의존성. 로그인은 user_db_session을 사용합니다."""
    async with user_db_session() as session:
        yield session


@contextmanager
def service_db_session() -> Iterator[Session]:
    """Celery·수집 등 내부 작업 전용 동기 세션."""
    maker = sessionmaker(_service_engine(), expire_on_commit=False)
    with maker() as session:
        with session.begin():
            yield session


def get_service_db() -> Iterator[Session]:
    """내부 작업용 의존성. 호출 전 API 권한 검사는 호출자가 담당합니다."""
    with service_db_session() as session:
        yield session
