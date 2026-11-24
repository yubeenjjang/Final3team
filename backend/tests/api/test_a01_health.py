import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from psycopg import OperationalError

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
    monkeypatch.setattr(health, "find_dotenv", lambda **_: "")
    monkeypatch.setattr(health, "dotenv_values", lambda _: {})
    monkeypatch.setenv("DB_USER_USERNAME", "noldaga_app")
    monkeypatch.setenv("DB_USER_PASSWORD", "fixture-password")
    monkeypatch.setenv("DB_HOST", "fixture.invalid")
    monkeypatch.setenv("DB_PORT", "55432")
    monkeypatch.setenv("DB_NAME", "fixture-db")
    connection = AsyncMock()
    connect = AsyncMock(return_value=connection)
    monkeypatch.setattr(health.AsyncConnection, "connect", connect)
    return connect, connection


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
    connect.assert_awaited_once_with(
        host="fixture.invalid", port=55432, dbname="fixture-db", user="noldaga_app",
        password="fixture-password", autocommit=True, options="-c statement_timeout=1000",
    )
    connection.execute.assert_awaited_once_with("SELECT 1")
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
    if failure == "configuration":
        monkeypatch.delenv("DB_USER_PASSWORD")
    elif failure == "connect":
        connect.side_effect = OperationalError("fixture DB connection error")
    elif failure == "query":
        connection.execute.side_effect = OperationalError("fixture DB query error")
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
