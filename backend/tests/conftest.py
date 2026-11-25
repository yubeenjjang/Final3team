import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

# API는 api.*를, 공통 DB 시험은 backend.*를 사용한다.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
for path in (_BACKEND_DIR.parent, _BACKEND_DIR):
    sys.path.insert(0, str(path))


@pytest.fixture(autouse=True)
def reset_route_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from api.auth.state import MemoryAuthState
    from api.services import route_rate_limit

    monkeypatch.setattr(route_rate_limit, "state", MemoryAuthState())


@pytest.fixture
def use_user_db(monkeypatch):
    from shared.db import session as sessions

    def bind(url, *, role=None):
        engine = create_async_engine(url, poolclass=NullPool, hide_parameters=True)
        if role is not None:
            event.listen(engine.sync_engine, "begin", lambda db: db.exec_driver_sql(f"SET LOCAL ROLE {role}"))
        monkeypatch.setattr(sessions, "_user_engine", lambda: engine)
        return engine

    return bind


@pytest.fixture
def use_sqlite_user_session(monkeypatch):
    def bind(module, engine):
        checkout = AsyncMock()

        @asynccontextmanager
        async def session(user_id=None):
            assert user_id is None
            with engine.begin() as db:
                yield AsyncMock(connection=checkout, execute=AsyncMock(side_effect=db.execute))

        monkeypatch.setattr(module, "user_db_session", session)
        return checkout

    return bind


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "db: 일회용 PostgreSQL DB를 사용하는 시험")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if not os.environ.get("TEST_DB_URL"):
        skip = pytest.mark.skip(reason="일회용 DB의 TEST_DB_URL이 없습니다.")
        for item in items:
            if item.get_closest_marker("db"):
                item.add_marker(skip)
