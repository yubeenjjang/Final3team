import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from api.main import app
from api.routers import health

_HEALTH = "/api/v1/health"
_DB_MODES = (
    {"FESTIVAL_DATA": "db"},
    {"AUTH_PROVIDER": "db"},
    {"ROUTE_PROVIDER": "real", "ROUTE_STORE": "db"},
    {"NOTICES_PROVIDER": "real"},
    {"TRANSIT_PROVIDER": "real"},
    {"VISIT_FORECAST_PROVIDER": "real", "VISIT_FORECAST_STORE": "db"},
)


@pytest.fixture
def db_connection(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    for mode in _DB_MODES:
        for name in mode:
            monkeypatch.delenv(name, raising=False)
    connection = AsyncMock()
    connect = AsyncMock(return_value=connection)

    @asynccontextmanager
    async def session(user_id):
        db = await connect(user_id=user_id)
        try:
            yield db
        finally:
            await db.close()

    monkeypatch.setattr(health, "user_db_session", session)
    return connect, connection


@pytest.mark.parametrize(("db_mode", "failures", "attempts"), [
    (False, 0, 0), (True, 0, 1), (True, 1, 2), (True, 3, 3),
])
def test_lifespan_prepares_db_with_bounded_retries(monkeypatch, db_connection, db_mode, failures, attempts):
    connect, connection = db_connection
    if db_mode:
        monkeypatch.setenv("AUTH_PROVIDER", "db")
    if failures:
        monkeypatch.setattr(health, "_DB_TIMEOUT_SECONDS", 0.05)
        remaining = iter([True] * failures)

        async def start_connection(**kwargs):
            if next(remaining, False):
                await asyncio.Event().wait()
            return connection

        connect.side_effect = start_connection

    with TestClient(app):
        assert connect.await_count == attempts


def test_a01_mock_does_not_connect(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_connection: tuple[AsyncMock, AsyncMock],
) -> None:
    monkeypatch.setenv("ROUTE_PROVIDER", "real")
    monkeypatch.setenv("VISIT_FORECAST_STORE", "db")
    response = client.get(_HEALTH)
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert response.headers["X-Mock"] == "true"
    connect, _ = db_connection
    connect.assert_not_awaited()


@pytest.mark.parametrize("mode", _DB_MODES)
def test_a01_db_executes_probe_as_app(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_connection: tuple[AsyncMock, AsyncMock],
    mode: dict[str, str],
) -> None:
    for name, value in mode.items():
        monkeypatch.setenv(name, value)
    connect, connection = db_connection
    response = client.get(_HEALTH)
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "db": "ok", "redis": "not_configured", "version": "0.1.0-mock", "is_mock": False,
    }
    assert "X-Mock" not in response.headers
    connect.assert_awaited_once_with(user_id=None)
    assert [str(call.args[0]) for call in connection.execute.await_args_list] == [
        "SET LOCAL statement_timeout = 1000", "SELECT 1",
    ]
    connection.close.assert_awaited_once()


@pytest.mark.parametrize("failure", ("configuration", "connect", "query", "connect_timeout", "query_timeout"))
def test_a01_returns_health_payload_on_db_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_connection: tuple[AsyncMock, AsyncMock],
    failure: str,
) -> None:
    async def stalled(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(5)

    monkeypatch.setenv("AUTH_PROVIDER", "db")
    connect, connection = db_connection
    db_error = OperationalError(None, None, OSError("fixture DB error"))
    if failure == "configuration":
        connect.side_effect = ValueError("fixture DB configuration error")
    elif failure == "connect":
        connect.side_effect = db_error
    elif failure == "query":
        connection.execute.side_effect = db_error
    elif failure == "connect_timeout":
        connect.side_effect = stalled
    else:
        connection.execute.side_effect = stalled

    response = client.get(_HEALTH)
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded", "db": "unavailable", "redis": "not_configured",
        "version": "0.1.0-mock", "is_mock": False,
    }
    assert "X-Mock" not in response.headers
    if failure in ("query", "query_timeout"):
        connection.close.assert_awaited_once()
