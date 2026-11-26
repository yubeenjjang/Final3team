import asyncio
import hmac
import json
import re
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from threading import Barrier, Event
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Client, MockTransport, Request, Response

from api.main import app
from api.providers.kakao import KakaoClient
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
from api.providers.tmap import TmapClient
from api.schemas.routes import ReturnRouteRequest, VisitRouteRequest
from api.services import real_routes
from . import FIXTURES, TEST_KEY

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
    monkeypatch.setenv("ROUTE_STORE", "memory")
    monkeypatch.setenv("ROUTE_KEY_SECRET", "TEST_KEY_DO_NOT_USE")
    monkeypatch.delenv("ROUTE_DEMO_SCENARIOS", raising=False)
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
        "route_request_id", "route_status", "direction", "festival_id", "origin",
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
    assert routes.client.get("/api/v1/health").headers["X-Mock"] == "true"


@pytest.mark.parametrize(("preference", "expected"), [
    ("fastest", ["c3", "c2", "c1"]),
    ("fewest_transfers", ["c1", "c3", "c2"]),
    ("min_walk", ["c2", "c1", "c3"]),
    ("less_crowded", ["c3", "c2", "c1"]),
    ("accessible", ["c3", "c2", "c1"]),
])
def test_real_candidate_order_matches_preference_across_cache_and_poll(routes, monkeypatch, preference, expected):
    monkeypatch.setenv("TMAP_APP_KEY", TEST_KEY)
    payload = json.loads((FIXTURES / "tmap_seoul.json").read_text())
    itineraries = payload["metaData"]["plan"]["itineraries"]
    sample = itineraries[0]
    itineraries[:] = [
        dict(sample, totalTime=duration * 60, transferCount=transfers, totalWalkDistance=walk)
        for duration, transfers, walk in [(19, 0, 600), (17, 2, 300), (17, 1, 800)]
    ]
    with Client(transport=MockTransport(lambda _: Response(200, json=payload))) as http:
        monkeypatch.setattr(routes.service, "_tmap", lambda: TmapClient(http))
        request = {**_BODY, "route_preference": preference}
        initial = routes.client.post(_RETURN, json=request)
        ready = _body(initial, 200)
        cached = _body(routes.client.post(_RETURN, json={**request, "request_id": "ranking-cache-01"}), 200)
        polled = _body(routes.client.get(
            f"{_RETURN}/{ready['route_request_id']}", headers={_TOKEN: initial.headers[_TOKEN]},
        ), 200)

    candidates = ready["route_candidates"]
    assert [candidate["candidate_id"] for candidate in candidates] == expected
    assert {candidate["candidate_id"]: candidate["duration_min"] for candidate in candidates} == {
        "c1": 19, "c2": 17, "c3": 17,
    }
    assert polled["route_candidates"] == cached["route_candidates"] == candidates
    assert routes.quota.calls == ["tmap"]


@pytest.mark.parametrize(("scenario", "http_status", "final_status", "error"), [
    ("sync_ready", 200, "ready", None),
    ("async_unavailable", 202, "unavailable", "ROUTE_UPSTREAM_ERROR"),
    ("async_timeout", 202, "timed_out", "ROUTE_TIMEOUT"),
    ("overloaded", 503, None, "ROUTE_OVERLOADED"),
])
def test_demo_return_scenarios(routes, monkeypatch, scenario, http_status, final_status, error):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ROUTE_DEMO_SCENARIOS", "true")
    monkeypatch.setenv("ROUTE_STORE", "db")
    headers = {"X-Mock-Scenario": scenario}
    response = routes.client.post(_RETURN, json={**_BODY, "request_id": f"demo-{scenario}"}, headers=headers)
    assert response.status_code == http_status and response.headers["X-Mock"] == "true"
    body = response.json()
    if final_status is None:
        assert body["error"]["code"] == error
    else:
        assert body["is_mock"] is True
        url = f"{_RETURN}/{body['route_request_id']}"
        headers[_TOKEN] = body["route_access_token"] if http_status == 202 else response.headers[_TOKEN]
        if http_status == 202:
            processing = routes.client.get(url, headers=headers)
            assert processing.headers["X-Mock"] == "true"
            assert processing.json()["route_status"] == "processing"
        else:
            url += "?candidate_id=c1"
        result = routes.client.get(url, headers=headers)
        assert result.status_code == 200 and result.headers["X-Mock"] == "true"
        assert result.json()["is_mock"] is True and result.json()["route_status"] == final_status
        if error:
            assert result.json()["error"]["code"] == error
        else:
            assert result.json()["route_candidates"][0]["candidate_id"] == "c1"
    assert not routes.quota.calls
    assert not routes.tmap.queries and not routes.kakao.queries and not routes.kakao.searches


def test_demo_visit_uses_header_for_submit_and_poll(routes, monkeypatch):
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("ROUTE_DEMO_SCENARIOS", "true")
    headers = {"X-Mock-Scenario": "async_ready"}
    response = routes.client.post(_VISIT, headers=headers, json={
        "request_id": "demo-visit-01", "festival_id": _BODY["festival_id"], "origin": _BODY["destination"],
    })
    assert response.status_code == 202 and response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    headers[_TOKEN] = body["route_access_token"]
    url = body["status_url"]
    no_header = routes.client.get(url, headers={_TOKEN: headers[_TOKEN]})
    assert no_header.status_code == 404 and "X-Mock" not in no_header.headers
    for status in ("processing", "ready"):
        result = routes.client.get(url, headers=headers)
        assert result.status_code == 200 and result.headers["X-Mock"] == "true"
        assert result.json()["is_mock"] is True and result.json()["route_status"] == status
    assert not routes.quota.calls


@pytest.mark.parametrize(("app_env", "enabled", "send_header"), [
    ("local", "true", False), ("local", "false", True), ("prod", "true", True),
])
def test_demo_inactive_keeps_real_submit_and_poll(routes, monkeypatch, app_env, enabled, send_header):
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("ROUTE_DEMO_SCENARIOS", enabled)
    headers = {"X-Mock-Scenario": "overloaded"} if send_header else {}
    response = routes.client.post(_RETURN, json=_BODY, headers=headers)
    body = _body(response, 200)
    result = routes.client.get(
        f"{_RETURN}/{body['route_request_id']}", headers={**headers, _TOKEN: response.headers[_TOKEN]},
    )
    assert _body(result, 200)["route_status"] == "ready"
    assert routes.quota.calls == ["tmap"]


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


def test_P9_visit_resolves_place_and_preserves_idempotency(routes: Routes) -> None:
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
    assert "route_access_token" not in ready

    route_id = ready["route_request_id"]
    checks = (
        (routes.client.get(f"{_VISIT}/{route_id}"), 401, "UNAUTHORIZED"),
        (routes.client.get(f"{_VISIT}/{route_id}", headers={_TOKEN: "다른 토큰".encode()}), 403, "FORBIDDEN"),
        (routes.client.get(f"{_RETURN}/{route_id}", headers={_TOKEN: "다른 토큰".encode()}), 404,
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
    assert re.fullmatch(r"v2:[0-9a-f]{64}", key)
    assert all(coordinate not in key for coordinate in ("37.5759", "126.9768", "37.5000", "126.9000"))


@pytest.mark.parametrize("conditions", [
    {"user_constraints": {"with_child": True}},
    {"user_constraints": {"wheelchair": True}},
    {"user_constraints": {"max_walk_m": 0}},
    {"route_preference": "min_walk"},
    {"travel_mode": "walk"},
])
def test_P23_cache_and_idempotency_distinguish_request_conditions(routes: Routes, conditions) -> None:
    first = _body(routes.client.post(_RETURN, json=_BODY), 200)
    same = _body(routes.client.post(_RETURN, json={
        **_BODY, "request_id": "same-conditions", "departure": "now",
        "user_constraints": {"max_walk_m": None, "wheelchair": False, "with_child": False},
    }), 200)
    assert len(routes.tmap.queries) == 1
    assert routes.service._records[first["route_request_id"]].route_key == (
        routes.service._records[same["route_request_id"]].route_key
    )

    different = _body(routes.client.post(_RETURN, json={
        **_BODY, **conditions, "request_id": "different-conditions",
    }), 200)
    assert routes.service._records[different["route_request_id"]].route_key != (
        routes.service._records[first["route_request_id"]].route_key
    )
    assert len(routes.tmap.queries) == 2
    conflict = _body(routes.client.post(_RETURN, json={**_BODY, **conditions}), 409)
    assert conflict["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_P23_route_key_includes_direction_departure_control_and_provider(routes: Routes) -> None:
    async def keys():
        request = ReturnRouteRequest(**_BODY)
        query = RouteQuery((37.5759, 126.9768), (37.5, 126.9), routes.clock.now)
        service = routes.service
        record = service._new_record("return", request, "", "", "", "")
        key = service._route_key(record, query, "tmap")
        assert key == service._route_key(record, query, "tmap")
        assert key != service._route_key(record, query, "kakao")

        record.control = real_routes.ControlSnapshot("cv2")
        assert key != service._route_key(record, query, "tmap")
        record.control = real_routes.ControlSnapshot()
        record.direction = "visit"
        record.request = VisitRouteRequest(**request.model_dump())
        assert key != service._route_key(record, query, "tmap")
        record.direction = "return"
        record.request = request
        record.depart_at += timedelta(minutes=5)
        assert key != service._route_key(record, query, "tmap")

        encoded = {
            "direction": "return", "festival_id": "fst_000001",
            "origin_type": "festival", "destination_type": "place",
            "origin": ["37.5759", "126.9768"], "destination": ["37.5000", "126.9000"],
            "travel_mode": "transit", "route_preference": "fastest",
            "user_constraints": {"with_child": False, "wheelchair": False, "max_walk_m": None},
            "departure": "now", "departure_bucket": int(routes.clock.now.timestamp()) // 300,
            "control_version": "none", "provider": "tmap",
        }
        normalized = json.dumps(encoded, sort_keys=True, separators=(",", ":"))
        expected = hmac.digest(TEST_KEY.encode(), f"route-key-v2:{normalized}".encode(), "sha256").hex()
        assert key == f"v2:{expected}"

    asyncio.run(keys())


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


def test_P23_kakao_fallback_uses_its_own_provider_key(routes: Routes) -> None:
    routes.clock.now -= timedelta(minutes=1)
    tmap = _body(routes.client.post(_RETURN, json=_BODY), 200)
    routes.clock.now += timedelta(seconds=61)
    routes.tmap.error = "temporary"
    kakao = _body(routes.client.post(_RETURN, json={**_BODY, "request_id": "kakao-fallback"}), 200)

    assert (tmap["provider"], kakao["provider"]) == ("tmap", "kakao")
    assert routes.service._records[tmap["route_request_id"]].route_key != (
        routes.service._records[kakao["route_request_id"]].route_key
    )
    assert not routes.service._cache


def test_P11_secondary_response_is_only_available_on_sync_post(routes: Routes) -> None:
    routes.tmap.error = "temporary"
    ready = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert ready["provider"] == "kakao"
    assert ready["provider_tier"] == "secondary"
    assert ready["completed_valid_route"] is True
    assert "route_access_token" not in ready
    failed = _body(routes.client.post(_RETURN, json=_BODY), 200)
    assert failed["route_status"] == "unavailable"
    assert failed["completed_valid_route"] is False
    assert failed["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
    assert failed["error"]["retryable"] is True
    assert "route_candidates" not in failed
    assert "route_access_token" not in failed
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
    assert "route_access_token" not in final
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
    routes.tmap.gate = Event()
    try:
        queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
    finally:
        routes.tmap.gate.set()
    routes.finish(queued["route_request_id"])
    routes.clock.now += timedelta(seconds=30)
    body = {**_BODY, "request_id": "real-route-02"}
    _body(routes.client.post(_RETURN, json=body), 200)
    assert len(routes.tmap.queries) == 1
    cached, = routes.service._cache.values()

    routes.clock.now += timedelta(seconds=31)
    expired = _poll(routes, queued)
    assert expired["route_status"] == "unavailable"
    assert expired["completed_valid_route"] is False
    assert expired["error"]["code"] == "ROUTE_RESULT_EXPIRED"
    assert expired["error"]["retryable"] is True
    assert expired["error"]["message"] == "경로가 만료됐어요. 다시 조회해 주세요."
    assert "route_candidates" not in expired
    assert cached.result is None
    assert not routes.service._cache

    _body(routes.client.post(_RETURN, json={**body, "request_id": "real-route-03"}), 200)
    assert len(routes.tmap.queries) == 2
    assert _body(routes.client.post(_RETURN, json=body), 200)["error"]["code"] == "ROUTE_RESULT_EXPIRED"


@pytest.mark.parametrize("result_state", ["missing", "purged-at-23h"])
def test_a05_db_ready_coverage_and_result_expiry(
    routes: Routes, monkeypatch: pytest.MonkeyPatch, result_state: str,
) -> None:
    routes.tmap.gate = Event()
    try:
        queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
    finally:
        routes.tmap.gate.set()
    routes.finish(queued["route_request_id"])

    class StoredRoute:
        result = {"queried_at": routes.clock.now, "purged_at": None, "candidates": [], "evidence": {}}

        def lookup(self, direction, route_id, token, now):
            assert direction == "return"
            assert route_id == queued["route_request_id"]
            assert hmac.compare_digest(token, queued["route_access_token"])
            return {
                "status": "ready",
                "completed_at": routes.clock.now,
                "error_detail": None,
                "festival_id": "fst_000001",
                "festival_lat": 37.5759,
                "festival_lng": 126.9768,
                "region_code": "SEOUL",
                "origin_type": "festival",
                "destination_type": "user",
                "travel_mode": "transit",
                "route_preference": "fastest",
                "constraints": {},
            }, self.result

    store = StoredRoute()
    monkeypatch.setattr(routes.service, "_store", store)
    ready = _poll(routes, queued)
    assert ready["route_status"] == "ready"
    assert ready["coverage"] == {"scope": "national", "region_code": "SEOUL", "supported": True}
    assert "route_access_token" not in ready

    store.result = (
        {"queried_at": routes.clock.now - timedelta(hours=23), "purged_at": routes.clock.now}
        if result_state == "purged-at-23h" else None
    )
    restored = _poll(routes, queued)
    assert restored["route_status"] == "unavailable"
    assert restored["completed_valid_route"] is False
    assert restored["error"] == {
        "code": "ROUTE_RESULT_EXPIRED",
        "message": "경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.",
        "retryable": False,
    }
    assert "route_candidates" not in restored


def test_a3_memory_expiry_removes_raw_places_from_all_cached_requests(
    routes: Routes, monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin_query, destination_query = "synthetic-private-origin", "synthetic-private-destination"
    origin, destination = (37.123412, 126.789112), (37.234512, 126.876512)
    places = {
        origin_query: (*origin, origin_query),
        destination_query: (*destination, destination_query),
    }
    monkeypatch.setattr(routes.kakao, "search_place", places.__getitem__)
    body = {
        **_BODY,
        "origin": {"lat": origin[0], "lng": origin[1]},
        "destination": {"query": destination_query},
    }
    cached_body = {
        **_BODY,
        "request_id": "privacy-cache-reuse",
        "origin": {"query": origin_query},
        "destination": {"lat": destination[0], "lng": destination[1]},
    }
    first = _body(routes.client.post(_RETURN, json=body), 200)
    second = _body(routes.client.post(_RETURN, json=cached_body), 200)
    assert first["origin"]["label"] == "37.123412,126.789112"
    assert first["destination"]["label"] == destination_query
    assert second["origin"]["label"] == origin_query
    assert second["destination"]["label"] == "37.234512,126.876512"
    assert len(routes.tmap.queries) == 1

    routes.clock.now += timedelta(seconds=60)
    replay = _body(routes.client.post(_RETURN, json=body), 200)
    assert replay["route_request_id"] == first["route_request_id"]
    assert replay["error"]["code"] == "ROUTE_RESULT_EXPIRED"
    assert not routes.service._cache and not routes.service._flights
    markers = ("37.1234", "126.7891", "37.2345", "126.8765", origin_query, destination_query)
    for record in (*routes.service._records.values(), *routes.service._request_keys.values()):
        retained = json.dumps(asdict(record), default=str)
        if any(raw in retained for raw in markers):
            pytest.fail("만료된 메모리 요청에 장소 원문이 남았습니다.", pytrace=False)

    assert _body(routes.client.post(_RETURN, json=cached_body), 200)["error"]["code"] == "ROUTE_RESULT_EXPIRED"
    assert routes.client.post(_RETURN, json={**body, "travel_mode": "walk"}).status_code == 409


@pytest.mark.parametrize("lane_key", ["Lane", "lane"])
def test_P13_tmap_all_candidates_running(
    routes: Routes, monkeypatch: pytest.MonkeyPatch, lane_key: str
) -> None:
    monkeypatch.setenv("TMAP_APP_KEY", TEST_KEY)
    payload = json.loads((FIXTURES / "tmap_seoul.json").read_text())
    itineraries = payload["metaData"]["plan"]["itineraries"]
    alternative = deepcopy(itineraries[0])
    alternative["legs"][1].update(
        service="0",
        **{lane_key: [{"service": "1", "route": "합성예시 급행"}]},
    )
    itineraries.append(alternative)

    with Client(transport=MockTransport(lambda _: Response(200, json=payload))) as http:
        monkeypatch.setattr(routes.service, "_tmap", lambda: TmapClient(http))
        ready = _body(routes.client.post(_RETURN, json=_BODY), 200)

    assert ready["route_status"] == "ready"
    assert ready["completed_valid_route"] is True
    assert [candidate["candidate_id"] for candidate in ready["route_candidates"]] == ["c1", "c2"]
    assert all(candidate["service_running"] is True for candidate in ready["route_candidates"])
    assert ready["route_candidates"][1]["legs"][1]["line"] == "합성예시 급행"
    assert "운행이 끝난 구간이 있어요" not in ready["notices"]
    assert routes.quota.calls == ["tmap"]


@pytest.mark.parametrize("all_ended", [False, True], ids=["partly_ended", "all_ended"])
def test_P13_tmap_excludes_ended_candidates(
    routes: Routes, monkeypatch: pytest.MonkeyPatch, all_ended: bool
) -> None:
    monkeypatch.setenv("TMAP_APP_KEY", TEST_KEY)
    payload = json.loads((FIXTURES / "tmap_seoul.json").read_text())
    itineraries = payload["metaData"]["plan"]["itineraries"]
    ended = deepcopy(itineraries[0])
    ended["legs"][1].update(service=0, Lane=[{"service": 0}])
    itineraries.insert(0, ended)
    if all_ended:
        itineraries[1]["legs"][1]["service"] = 0

    with Client(transport=MockTransport(lambda _: Response(200, json=payload))) as http:
        monkeypatch.setattr(routes.service, "_tmap", lambda: TmapClient(http))
        result = _body(routes.client.post(_RETURN, json=_BODY), 200)
        replay = _body(routes.client.post(_RETURN, json=_BODY), 200)

    assert routes.quota.calls == ["tmap"]
    assert not routes.kakao.queries
    assert "운행이 끝난 구간이 있어요" in result["notices"]
    if all_ended:
        assert result["route_status"] == "unavailable"
        assert result["completed_valid_route"] is False
        assert result["error"] == {
            "code": "ROUTE_NO_RESULT", "message": "지금은 대중교통으로 갈 수 없어요", "retryable": False,
        }
        assert "route_candidates" not in result
        assert not routes.service._cache
    else:
        assert result["route_status"] == "ready"
        assert result["completed_valid_route"] is True
        candidate, = result["route_candidates"]
        assert candidate["candidate_id"] == "c2"
        assert candidate["service_running"] is True
    assert replay == result
    assert "route_access_token" not in result


def test_P14_tmap_service_ended_after_202(
    routes: Routes, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(real_routes, "_SYNC_WAIT_S", 0.2)
    monkeypatch.setenv("TMAP_APP_KEY", TEST_KEY)
    payload = json.loads((FIXTURES / "tmap_seoul.json").read_text())
    payload["metaData"]["plan"]["itineraries"][0]["legs"][1]["service"] = 0
    gate = Event()

    def handler(_: Request) -> Response:
        assert gate.wait(2)
        return Response(200, json=payload)

    with Client(transport=MockTransport(handler)) as http:
        monkeypatch.setattr(routes.service, "_tmap", lambda: TmapClient(http))
        try:
            queued = _body(routes.client.post(_RETURN, json=_BODY), 202)
        finally:
            gate.set()
        routes.finish(queued["route_request_id"])
        final = _poll(routes, queued)

    assert final["route_status"] == "unavailable"
    assert final["completed_valid_route"] is False
    assert final["error"] == {
        "code": "ROUTE_NO_RESULT", "message": "지금은 대중교통으로 갈 수 없어요", "retryable": False,
    }
    assert "운행이 끝난 구간이 있어요" in final["notices"]
    assert "route_candidates" not in final
    assert routes.quota.calls == ["tmap"]
    assert not routes.kakao.queries


def test_P14_kakao_last_service_unknown_in_sync_response(
    routes: Routes, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KAKAO_REST_API_KEY", TEST_KEY)
    routes.tmap.error = "no_result"
    payload = json.loads((FIXTURES / "kakao_transit_seoul.json").read_text())

    with Client(transport=MockTransport(lambda _: Response(200, json=payload))) as http:
        monkeypatch.setattr(routes.service, "_kakao", lambda: KakaoClient(http))
        ready = _body(routes.client.post(_RETURN, json=_BODY), 200)
        replay = _body(routes.client.post(_RETURN, json=_BODY), 200)

    assert routes.quota.calls == ["tmap", "kakao"]
    assert ready["route_status"] == "ready"
    assert ready["provider_tier"] == "secondary"
    candidate, = ready["route_candidates"]
    assert candidate["service_running"] is None
    assert "막차 확인 불가" in ready["notices"]
    assert replay["error"]["code"] == "ROUTE_SECONDARY_SYNC_ONLY"
    assert "route_candidates" not in replay
    assert not routes.service._cache
