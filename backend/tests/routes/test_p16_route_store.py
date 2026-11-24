import asyncio
import json
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import TimeoutError as DBPoolTimeout

from api.errors import ApiError
from api.main import app
from api.providers.route_base import ProviderResult
from api.repositories.route_store import TOKEN_TTL, RouteStore, stored_candidates, token_hash
from api.schemas.routes import ReturnRouteRequest
from api.services import real_routes
from shared.db import session as db_sessions
from tests.routes.test_p9_real_routes import Clock, FakeProvider


def test_P16_db_candidates_exclude_geometry_and_raw_fields():
    result = ProviderResult("tmap", "primary", Clock().now.isoformat(), [{
        "candidate_id": "c1", "summary": "버스 1회", "destination": "사용자 입력",
        "legs": [{
            "mode": "bus", "line": "110", "path": [[37.123456, 126.123456]],
            "stops": [{"id": "1", "name": "합성 정류장", "lat": 37.123456, "lng": 126.123456}],
        }],
    }], [])
    candidate, = stored_candidates(result)
    assert candidate["candidate_id"] == "c1"
    assert "destination" not in candidate
    assert candidate["legs"] == [{
        "mode": "bus", "line": "110", "stops": [{"id": "1", "name": "합성 정류장"}],
    }]
    result.provider = "kakao"
    with pytest.raises(ValueError, match="TMAP"):
        stored_candidates(result)


@pytest.mark.parametrize(("token", "elapsed", "status"), [
    ("synthetic-other", timedelta(), 403),
    ("synthetic-valid", TOKEN_TTL, 401),
])
def test_P16_db_checks_token_before_reading_result(token, elapsed, status):
    clock = Clock()
    request = {"access_token_hash": token_hash("synthetic-valid"), "submitted_at": clock.now, "status": "ready"}
    calls = []

    def execute(statement, params):
        calls.append(str(statement))
        return SimpleNamespace(mappings=lambda: SimpleNamespace(one_or_none=lambda: request))

    store = RouteStore(lambda: nullcontext(SimpleNamespace(execute=execute)))
    with pytest.raises(ApiError) as error:
        store.lookup("return", "rr_SYNTHETIC", token, clock.now + elapsed)
    assert error.value.status == status
    assert len(calls) == 1
    assert "route_results" not in calls[0]


def test_P17_db_replay_keeps_request_id_after_token_expiry(monkeypatch):
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    clock = Clock()
    submitted_at = clock.now
    route_id = "rr_SYNTHETIC"
    lookups = []

    def execute(statement, params):
        if "WHERE request_id = :request_id" in str(statement):
            row = SimpleNamespace(route_request_id=route_id, request_body_hash=body_hash)
            return SimpleNamespace(one_or_none=lambda: row)
        assert "WHERE route_request_id = :route_id" in str(statement)
        lookups.append(params["route_id"])
        row = {"access_token_hash": access_token_hash, "submitted_at": submitted_at, "status": "ready"}
        return SimpleNamespace(mappings=lambda: SimpleNamespace(one_or_none=lambda: row))

    store = RouteStore(lambda: nullcontext(SimpleNamespace(execute=execute)))
    service = real_routes.RealRouteService(now=lambda: clock.now, store=store)
    body = {
        "request_id": "synthetic-replay-request", "festival_id": "fst_000001",
        "destination": {"lat": 37.123456, "lng": 126.789123},
    }
    request = ReturnRouteRequest(**body)
    body_hash = service._private_hash("request-body", json.dumps(body, sort_keys=True))
    token = service._db_token(route_id)
    access_token_hash = token_hash(token)
    clock.now += TOKEN_TTL

    status, replay = asyncio.run(service.create_route("return", request, body))
    assert status == 200
    assert replay["route_request_id"] == route_id
    assert replay["route_status"] == "unavailable"
    assert replay["completed_valid_route"] is False
    assert replay["error"]["code"] == "ROUTE_ACCESS_EXPIRED"
    assert replay["error"]["retryable"] is False
    assert {"route_access_token", "route_candidates", "status_url"}.isdisjoint(replay)

    with pytest.raises(ApiError) as error:
        asyncio.run(service.get_route_response("return", route_id, token))
    assert error.value.status == 401
    assert lookups == [route_id, route_id]


def test_P16_store_flag_defaults_to_memory(monkeypatch):
    real_routes.get_service.cache_clear()
    try:
        monkeypatch.delenv("ROUTE_STORE", raising=False)
        assert real_routes.get_service()._store is None
        real_routes.get_service.cache_clear()
        monkeypatch.setenv("ROUTE_STORE", "db")
        monkeypatch.delenv("ROUTE_KEY_SECRET", raising=False)
        with pytest.raises(ApiError) as error:
            real_routes.get_service()
        assert error.value.status == 503
    finally:
        real_routes.get_service.cache_clear()


def test_P20_shared_service_settings_error_returns_503(monkeypatch):
    def missing_settings():
        raise ValueError("합성 DB 설정 오류")

    monkeypatch.setattr(db_sessions, "_service_engine", missing_settings)

    with pytest.raises(ApiError) as error:
        RouteStore().lookup("return", "rr_SYNTHETIC", "synthetic-token", Clock().now)

    assert error.value.status == 503
    assert error.value.code == "ROUTE_STORE_UNAVAILABLE"
    assert error.value.__suppress_context__


@pytest.mark.parametrize("method", ["POST", "GET"])
def test_P24_pool_timeout_returns_retryable_service_busy(monkeypatch, caplog, method):
    def exhausted_pool():
        raise DBPoolTimeout("synthetic internal pool details")

    monkeypatch.setenv("ROUTE_PROVIDER", "real")
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    service = real_routes.RealRouteService(store=RouteStore(exhausted_pool))
    monkeypatch.setattr(real_routes, "get_service", lambda: service)
    path = "/api/v1/routes/return"
    headers = {"X-Request-ID": "synthetic-pool-request", "Origin": "http://localhost:3000"}
    with TestClient(app) as client:
        if method == "POST":
            response = client.post(path, headers=headers, json={
                "request_id": "synthetic-pool-request",
                "festival_id": "fst_000001",
                "destination": {"lat": 37.5, "lng": 126.9},
            })
        else:
            response = client.get(f"{path}/rr_SYNTHETIC", headers={
                **headers, "X-Route-Access-Token": "synthetic-token",
            })

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "1"
    assert "Retry-After" in response.headers["Access-Control-Expose-Headers"]
    assert response.headers["X-Request-ID"] == headers["X-Request-ID"]
    assert "X-Mock" not in response.headers
    assert response.json() == {"error": {
        "code": "DB_POOL_TIMEOUT",
        "message": "요청이 많아 잠시 후 다시 시도해 주세요.",
        "request_id": headers["X-Request-ID"],
        "retryable": True,
    }}
    assert "synthetic internal pool details" not in caplog.text


@pytest.mark.parametrize("tmap_available", [True, False])
def test_P17_db_write_contains_only_the_allowed_result(monkeypatch, tmap_available):
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    clock = Clock()
    writes = []

    def register(values):
        writes.append(("queued", values))
        return True

    def finish(route_id, now, route_key, **values):
        writes.append((values["status"], values))

    store = SimpleNamespace(
        request_for_retry=lambda request_id, body_hash: None,
        register=register,
        start=lambda route_id, now: writes.append(("processing", {})),
        finish=finish,
    )
    tmap = FakeProvider("tmap", clock, error=None if tmap_available else "temporary")
    kakao = FakeProvider("kakao", clock)
    service = real_routes.RealRouteService(
        tmap=lambda: tmap, kakao=lambda: kakao,
        quota=SimpleNamespace(try_acquire=lambda provider: True), now=lambda: clock.now, store=store,
    )
    body = {
        "request_id": "synthetic-privacy-request", "festival_id": "fst_000001",
        "destination": {"lat": 37.123456, "lng": 126.789123},
    }
    status, response = asyncio.run(service.create_route("return", ReturnRouteRequest(**body), body))
    assert status == 200
    assert "route_access_token" not in response
    assert [name for name, _ in writes] == [
        "queued", "processing", "ready" if tmap_available else "unavailable",
    ]
    token = service._db_token(response["route_request_id"])
    assert writes[0][1]["token_hash"] == token_hash(token)
    serialized_writes = json.dumps(writes, default=str)
    for sensitive in (token, body["request_id"], "37.123456", "126.789123"):
        assert sensitive not in serialized_writes
    if tmap_available:
        assert writes[-1][1]["result"] is not None
    else:
        assert response["provider"] == "kakao"
        assert writes[-1][1]["result"] is None
        assert writes[-1][1]["error_code"] == "ROUTE_SECONDARY_SYNC_ONLY"
