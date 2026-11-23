import asyncio
import hashlib
import hmac
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Barrier, Event
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from api.main import app
from api.providers.quota import QuotaProvider
from api.providers.route_base import (
    KST,
    ErrorKind,
    ProviderError,
    ProviderName,
    ProviderResult,
    RouteQuery,
    make_candidate,
)
from api.services import real_routes

_RETURN = "/api/v1/routes/return"
_VISIT = "/api/v1/routes/visit"
_TOKEN = "X-Route-Access-Token"
_BODY = {
    "request_id": "real-route-01", "festival_id": "fst_000001",
    "destination": {"lat": 37.5, "lng": 126.9},
}


@dataclass
class Clock:
    now: datetime = datetime(2026, 11, 23, 12, 4, tzinfo=KST)


@dataclass
class FakeProvider:
    name: ProviderName
    clock: Clock
    error: ErrorKind | None = None
    search_error: ErrorKind | None = None
    gate: Event | None = None
    entered: Event = field(default_factory=Event)
    queries: list[RouteQuery] = field(default_factory=list)
    searches: list[str] = field(default_factory=list)

    def query(self, query: RouteQuery) -> ProviderResult:
        self.queries.append(query)
        self.entered.set()
        if self.gate is not None and not self.gate.wait(8):
            raise ProviderError("timeout", self.name)
        if self.error is not None:
            raise ProviderError(self.error, self.name)
        result = make_candidate(
            1, duration_min=16, distance_m=1800, walk_m=400, transfers=0, fare_krw=1550,
            legs=[{"mode": "bus", "duration_min": 16, "path": [query.origin, query.destination]}],
            service_running=True,
            bus_crowding={"status": "unsupported", "reason": "혼잡 정보가 없어요."},
        )
        tier = "primary" if self.name == "tmap" else "secondary"
        return ProviderResult(self.name, tier, self.clock.now.isoformat(), [result], [])

    def search_place(self, query: str) -> tuple[float, float, str]:
        self.searches.append(query)
        if self.search_error is not None:
            raise ProviderError(self.search_error, self.name)
        return 37.5, 126.9, "검색 결과 이름"


@dataclass
class FakeQuota:
    unavailable: set[QuotaProvider] = field(default_factory=set)
    calls: list[QuotaProvider] = field(default_factory=list)

    def try_acquire(self, provider: QuotaProvider) -> bool:
        self.calls.append(provider)
        return provider not in self.unavailable


@dataclass
class Routes:
    client: TestClient
    service: real_routes.RealRouteService
    clock: Clock
    tmap: FakeProvider
    kakao: FakeProvider
    quota: FakeQuota

    def finish(self, route_id: str) -> None:
        async def wait_until_finished() -> None:
            task = self.service._records[route_id].task
            if task is not None:
                await asyncio.wait_for(asyncio.shield(task), timeout=2)

        assert self.client.portal is not None
        self.client.portal.call(wait_until_finished)


@pytest.fixture
def routes(monkeypatch: pytest.MonkeyPatch) -> Iterator[Routes]:
    monkeypatch.setenv("ROUTE_PROVIDER", "real")
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    clock = Clock()
    tmap, kakao = FakeProvider("tmap", clock), FakeProvider("kakao", clock)
    quota = FakeQuota()
    service = real_routes.RealRouteService(
        tmap=lambda: tmap, kakao=lambda: kakao, quota=quota, now=lambda: clock.now,
    )
    monkeypatch.setattr(real_routes, "get_service", lambda: service)
    with TestClient(app) as client:
        try:
            yield Routes(client, service, clock, tmap, kakao, quota)
        finally:
            for provider in (tmap, kakao):
                if provider.gate is not None:
                    provider.gate.set()


def _body(response: Response, status: int) -> dict[str, Any]:
    assert response.status_code == status
    assert "X-Mock" not in response.headers
    assert response.headers["X-Request-ID"]
    body = response.json()
    if status < 400:
        assert body["is_mock"] is False
    else:
        assert body["error"]["request_id"] == response.headers["X-Request-ID"]
    return body


def _poll(routes: Routes, route: dict[str, Any], path: str = _RETURN) -> dict[str, Any]:
    url = f"{path}/{route['route_request_id']}"
    return _body(routes.client.get(url, headers={_TOKEN: route["route_access_token"]}), 200)


def test_P9_primary_preserves_response_shape_and_ignores_mock_scenario(routes: Routes) -> None:
    ready = _body(routes.client.post(_RETURN, json=_BODY, headers={"X-Mock-Scenario": "overloaded"}), 200)
    assert set(ready) == {
        "route_request_id", "route_status", "route_access_token", "direction", "festival_id", "origin",
        "destination", "travel_mode", "route_preference", "route_candidates", "provider", "provider_tier",
        "queried_at", "verification_status", "completed_valid_route", "constraint_status", "coverage",
        "score_version", "notices", "is_mock",
    }
    assert ready["provider"] == "tmap"
    assert ready["provider_tier"] == "primary"
    assert ready["route_status"] == "ready"
    assert ready["completed_valid_route"] is True
    assert ready["destination"] == {"type": "place", "label": "37.5,126.9"}
    assert routes.tmap.queries == [RouteQuery((37.5759, 126.9768), (37.5, 126.9), routes.clock.now)]
    assert routes.quota.calls == ["tmap"]
    assert _poll(routes, ready) == {**ready, "updated_at": routes.clock.now.isoformat()}
    assert routes.client.get("/api/v1/health").headers["X-Mock"] == "true"


@pytest.mark.parametrize("mode", [None, "mock"])
def test_P9_mock_mode_does_not_select_real_service(
    routes: Routes, monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    if mode is None:
        monkeypatch.delenv("ROUTE_PROVIDER")
    else:
        monkeypatch.setenv("ROUTE_PROVIDER", mode)
    response = routes.client.post(_RETURN, json=_BODY, headers={"X-Mock-Scenario": "sync_ready"})
    assert response.status_code == 200
    assert response.headers["X-Mock"] == "true"
    assert response.json()["is_mock"] is True
    assert not routes.quota.calls


def test_P9_visit_resolves_place_and_preserves_tokens_and_idempotency(routes: Routes) -> None:
    body = {
        "request_id": "real-visit-01", "festival_id": "fst_000001", "origin": {"query": "서울역"},
        "user_constraints": {"with_child": True, "wheelchair": True, "max_walk_m": 0},
    }
    ready = _body(routes.client.post(_VISIT, json=body), 200)
    assert ready["direction"] == "visit"
    assert ready["origin"] == {"type": "place", "label": "서울역"}
    assert ready["destination"]["type"] == "festival"
    assert ready["constraint_status"] == {
        "control": "unverified", "with_child": "not_verifiable",
        "wheelchair": "not_verifiable", "max_walk_m": "not_verifiable",
    }
    assert routes.tmap.queries[0].origin == (37.5, 126.9)
    assert routes.kakao.searches == ["서울역"]
    assert routes.quota.calls == ["kakao_local", "tmap"]
    assert _body(routes.client.post(_VISIT, json=dict(reversed(list(body.items())))), 200) == ready
    assert routes.kakao.searches == ["서울역"]
    assert _poll(routes, ready, _VISIT)["route_status"] == "ready"

    route_id = ready["route_request_id"]
    checks = (
        (routes.client.get(f"{_VISIT}/{route_id}"), 401, "UNAUTHORIZED"),
        (routes.client.get(f"{_VISIT}/{route_id}", headers={_TOKEN: "다른 토큰".encode()}), 403, "FORBIDDEN"),
        (routes.client.get(f"{_RETURN}/{route_id}", headers={_TOKEN: ready["route_access_token"]}), 404,
         "ROUTE_REQUEST_NOT_FOUND"),
        (routes.client.get(f"{_VISIT}/rr_invalid-id"), 422, "VALIDATION_ERROR"),
        (routes.client.post(_VISIT, json={**body, "origin": {"query": "다른 장소"}}), 409,
         "IDEMPOTENCY_CONFLICT"),
    )
    for response, status, code in checks:
        assert _body(response, status)["error"]["code"] == code


def test_P10_festival_and_place_validation_precedes_provider_calls(routes: Routes) -> None:
    body = {**_BODY, "destination": {"query": "검색할 장소"}}
    routes.kakao.search_error = "no_result"
    missing = _body(routes.client.post(_RETURN, json={**body, "festival_id": "fst_999999"}), 404)
    no_coordinates = _body(routes.client.post(_RETURN, json={**body, "festival_id": "fst_000006"}), 400)
    unknown_place = _body(routes.client.post(_RETURN, json=body), 400)
    assert missing["error"]["code"] == "FESTIVAL_NOT_FOUND"
    assert no_coordinates["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    assert unknown_place["error"]["code"] == "ROUTE_INVALID"
    assert routes.kakao.searches == ["검색할 장소"]
    assert routes.quota.calls == ["kakao_local"]
    assert not routes.tmap.queries and not routes.kakao.queries


@pytest.mark.parametrize("both", [False, True])
def test_P10_quota_skips_route_provider_calls(routes: Routes, both: bool) -> None:
    routes.quota.unavailable.add("tmap")
    if both:
        routes.quota.unavailable.add("kakao")
    body = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert not routes.tmap.queries
    assert routes.quota.calls == ["tmap", "kakao"]
    if both:
        assert not routes.kakao.queries
        assert body["error"]["code"] == "ROUTE_QUOTA_EXCEEDED"
        assert body["error"]["retryable"] is False
    else:
        assert body["provider"] == "kakao"
        assert len(routes.kakao.queries) == 1


@pytest.mark.parametrize("kind", ["too_close", "bad_request"])
def test_P10_invalid_primary_route_does_not_fall_back(routes: Routes, kind: ErrorKind) -> None:
    routes.tmap.error = kind
    failure = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert failure["route_status"] == "unavailable"
    assert failure["completed_valid_route"] is False
    code = "ROUTE_NO_RESULT" if kind == "too_close" else "ROUTE_INVALID"
    assert failure["error"]["code"] == code
    assert failure["error"]["retryable"] is False
    if kind == "too_close":
        assert failure["error"]["message"] == "걸어서 갈 수 있는 거리예요"
    assert not routes.kakao.queries
    assert routes.quota.calls == ["tmap"]


def test_P10_cache_key_uses_hmac_and_rounded_coordinates(routes: Routes) -> None:
    original = _body(routes.client.post(_RETURN, json=_BODY), 200)
    second = _body(routes.client.post(_RETURN, json={
        **_BODY, "request_id": "real-route-02", "destination": {"lat": 37.50001, "lng": 126.90001},
    }), 200)
    assert original["route_request_id"] != second["route_request_id"]
    assert second["destination"]["label"] == "37.50001,126.90001"
    assert original["route_candidates"] == second["route_candidates"]
    assert len(routes.tmap.queries) == 1
    key, = routes.service._cache
    departure_bucket = int(routes.clock.now.timestamp()) // 300
    encoded = f"return|37.5759,126.9768|37.5000,126.9000|transit|fastest|{departure_bucket}".encode()
    assert key == hmac.new(b"TEST_KEY_DO_NOT_USE", encoded, hashlib.sha256).hexdigest()
    assert all(coordinate not in key for coordinate in ("37.5759", "126.9768", "37.5000", "126.9000"))


def test_P10_five_concurrent_requests_share_one_tmap_call(routes: Routes) -> None:
    routes.tmap.gate = Event()
    start = Barrier(5)

    def submit(index: int) -> Response:
        start.wait(timeout=2)
        return routes.client.post(_RETURN, json={**_BODY, "request_id": f"real-parallel-{index}"})

    async def wait_for_five_requests() -> None:
        async with asyncio.timeout(2):
            while len(routes.service._records) != 5:
                await asyncio.sleep(0.01)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(submit, index) for index in range(5)]
        try:
            assert routes.client.portal is not None
            routes.client.portal.call(wait_for_five_requests)
            assert routes.tmap.entered.wait(2)
        finally:
            routes.tmap.gate.set()
        ready = [_body(future.result(timeout=3), 200) for future in futures]
    assert len({response["route_request_id"] for response in ready}) == 5
    assert all(response["route_status"] == "ready" for response in ready)
    assert len(routes.tmap.queries) == 1
    assert routes.quota.calls == ["tmap"]


def test_P11_secondary_response_is_only_available_on_sync_post(routes: Routes) -> None:
    routes.tmap.error = "temporary"
    ready = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert ready["provider"] == "kakao"
    assert ready["provider_tier"] == "secondary"
    assert ready["completed_valid_route"] is True
    failed = _poll(routes, ready)
    assert failed["route_status"] == "unavailable"
    assert failed["completed_valid_route"] is False
    assert failed["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
    assert failed["error"]["retryable"] is True
    assert "route_candidates" not in failed
    replay = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert replay == {**failed, "route_access_token": ready["route_access_token"]}
    assert not routes.service._cache and not routes.service._flights
    record = routes.service._records[ready["route_request_id"]]
    assert record.cached is None and record.task is None
    assert len(routes.kakao.queries) == 1


@pytest.mark.parametrize("primary_fails", [False, True])
def test_P11_slow_primary_returns_202_then_finishes_in_background(
    routes: Routes, primary_fails: bool
) -> None:
    routes.tmap.gate = Event()
    if primary_fails:
        routes.tmap.error = "temporary"
    queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
    assert queued == {
        "route_request_id": queued["route_request_id"], "route_status": "queued",
        "status_url": f"{_RETURN}/{queued['route_request_id']}",
        "route_access_token": queued["route_access_token"], "retry_after_s": 2, "is_mock": False,
    }
    assert _poll(routes, queued)["route_status"] == "processing"
    routes.tmap.gate.set()
    routes.finish(queued["route_request_id"])
    final = _poll(routes, queued)
    if primary_fails:
        assert final["route_status"] == "unavailable"
        assert final["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
        assert final["error"]["retryable"] is True
    else:
        assert final["route_status"] == "ready"
        assert final["provider"] == "tmap"
    assert not routes.kakao.queries
    assert routes.quota.calls == ["tmap"]
    assert _body(routes.client.post(_RETURN, json=_BODY), 202) == queued


def test_P11_secondary_in_flight_at_202_is_never_replayed(
    routes: Routes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 0.2)
    routes.tmap.error = "temporary"
    routes.kakao.gate = Event()
    queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
    assert routes.kakao.entered.is_set()
    routes.kakao.gate.set()
    routes.finish(queued["route_request_id"])
    final = _poll(routes, queued)
    assert final["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
    assert "route_candidates" not in final
    assert not routes.service._cache and not routes.service._flights


def test_P11_overall_deadline_times_out_and_releases_flight(
    routes: Routes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 0.1)
    monkeypatch.setattr(real_routes, "_REQUEST_LIMIT_S", 0.3)
    monkeypatch.setattr(real_routes, "_FLIGHT_LIMIT_S", 0.6)
    routes.tmap.gate = Event()
    queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
    routes.finish(queued["route_request_id"])
    failed = _poll(routes, queued)
    assert failed["route_status"] == "timed_out"
    assert failed["error"]["code"] == "ROUTE_TIMEOUT"
    assert failed["error"]["retryable"] is True
    assert not routes.kakao.queries

    async def wait_for_flight_expiry() -> None:
        flight, = routes.service._flights.values()
        await asyncio.wait_for(asyncio.shield(flight), timeout=2)

    assert routes.client.portal is not None
    routes.client.portal.call(wait_for_flight_expiry)
    assert not routes.service._flights
    assert not routes.service._cache
    routes.tmap.gate.set()
    retry = _body(routes.client.post(_RETURN, json={**_BODY, "request_id": "real-route-02"}), 200)
    assert retry["route_status"] == "ready"
    assert len(routes.tmap.queries) == 2


def test_P11_expiry_removes_shared_tmap_body_for_all_ids(routes: Routes) -> None:
    ready = _body(routes.client.post(_RETURN, json=_BODY), 200)
    routes.clock.now += timedelta(seconds=30)
    body = {**_BODY, "request_id": "real-route-02"}
    second = _body(routes.client.post(_RETURN, json=body), 200)
    assert len(routes.tmap.queries) == 1
    cached, = routes.service._cache.values()

    routes.clock.now += timedelta(seconds=31)
    expired = _poll(routes, ready)
    assert expired["route_status"] == "unavailable"
    assert expired["completed_valid_route"] is False
    assert expired["error"]["code"] == "ROUTE_RESULT_EXPIRED"
    assert expired["error"]["retryable"] is True
    assert "route_candidates" not in expired
    assert cached.result is None
    assert not routes.service._cache

    _body(routes.client.post(_RETURN, json={**body, "request_id": "real-route-03"}), 200)
    assert len(routes.tmap.queries) == 2
    assert _poll(routes, second)["error"]["code"] == "ROUTE_RESULT_EXPIRED"
