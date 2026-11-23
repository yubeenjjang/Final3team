import asyncio
import json
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.mocks.store import festivals
from api.providers import seoul_citydata
from api.providers.seoul_citydata import SeoulCityData
from api.services import seoul_crowd
from api.services.seoul_areas import SeoulArea, SeoulAreaCatalog, load_catalog
from api.services.seoul_crowd import SeoulCrowdService

_FESTIVAL = "fst_000001"
_URL = f"/api/v1/festivals/{_FESTIVAL}/crowd"
_NOW = datetime.fromisoformat("2026-11-19T17:26:00+09:00")
_TEST_KEY = "TEST_KEY_DO_NOT_USE"
_LEGACY_KEYS = {"is_mock", "festival_id", "status", "coverage", "source", "observed_at",
                "notices", "error", "areas"}


def _body(name: str) -> dict:
    path = Path(__file__).with_name("fixtures") / f"citydata_ppltn_{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _reading_for(area_code: str, name: str = "observed") -> dict:
    body = _body(name)
    body["SeoulRtd.citydata_ppltn"][0]["AREA_CD"] = area_code
    return body


def _area(code: str, offset: float = 0) -> SeoulArea:
    festival = festivals[_FESTIVAL]
    south = festival.lat - 0.0001 + offset
    west = festival.lng - 0.0001
    north, east = south + 0.0002, west + 0.0002
    return SeoulArea(code, f"구역 {code}", [[[
        (south, west), (north, west), (north, east), (south, east), (south, west),
    ]]])


def _request_area(request: httpx2.Request) -> str:
    assert request.url.path.split("/")[2:-1] == ["json", "citydata_ppltn", "1", "1"]
    assert request.method == "GET"
    return request.url.path.rsplit("/", 1)[1]


def _service(handler: Callable, **kwargs) -> SeoulCrowdService:
    provider = SeoulCityData(transport=httpx2.MockTransport(handler))
    return SeoulCrowdService(provider, **({"now": lambda: _NOW} | kwargs))


@pytest.fixture(autouse=True)
def defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", _TEST_KEY)
    monkeypatch.setenv("CROWD_QUOTA_FILE", str(tmp_path / "crowd.json"))
    monkeypatch.delenv("CROWD_SEOUL_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("CROWD_PROVIDER", raising=False)
    monkeypatch.setenv("FESTIVAL_DATA", "mock")
    _set_areas(monkeypatch, (_area("POI009"),))


def _set_areas(monkeypatch: pytest.MonkeyPatch, areas: tuple[SeoulArea, ...]) -> None:
    catalog = SeoulAreaCatalog(areas, load_catalog().source_url)
    monkeypatch.setattr(seoul_crowd, "load_catalog", lambda: catalog)


def _observed(request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(200, json=_reading_for(_request_area(request)))


def _unexpected(_: httpx2.Request) -> httpx2.Response:
    pytest.fail("공급원을 호출하면 안 됩니다.")


@pytest.mark.parametrize(
    ("scenario", "status"), [(None, "ok"), ("stale", "stale"), ("source_error", "unavailable")]
)
def test_P5_default_mock_keeps_headers_and_legacy_response(monkeypatch, scenario, status) -> None:
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: _service(_unexpected))
    headers = {"X-Mock-Scenario": scenario} if scenario else {}
    with TestClient(app) as client:
        response = client.get(_URL, headers=headers)
    assert response.headers["X-Mock"] == "true"
    assert response.json().keys() == _LEGACY_KEYS
    assert response.json()["is_mock"] is True
    assert response.json()["status"] == status


@pytest.mark.parametrize("fixture", ["observed", "replacement"])
def test_P2_P3_real_headers_legacy_keys_and_labels(monkeypatch, fixture) -> None:
    now = _NOW if fixture == "observed" else datetime.fromisoformat("2026-11-23T15:55:00+09:00")
    service = _service(lambda _: httpx2.Response(200, json=_body(fixture)), now=lambda: now)
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: service)
    monkeypatch.setenv("CROWD_PROVIDER", "real")
    with TestClient(app) as client:
        response = client.get(_URL, headers={"X-Mock-Scenario": "source_error", "X-Request-ID": "w89"})
        unrelated = client.get(f"/api/v1/festivals/{_FESTIVAL}/weather")
        unknown = client.get("/api/v1/festivals/fst_abcdef/crowd")
        malformed = client.get("/api/v1/festivals/invalid/crowd")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "w89"
    assert "X-Mock" not in response.headers
    assert unrelated.headers["X-Mock"] == "true"
    assert unknown.status_code == 404 and "X-Mock" not in unknown.headers
    assert malformed.status_code == 422 and "X-Mock" not in malformed.headers

    body = response.json()
    assert _LEGACY_KEYS <= body.keys()
    assert body["is_mock"] is False and body["status"] == "ok"
    (area,) = body["nearby_areas"]
    assert area["distance_m"] == 0
    assert area["data"] == body["areas"][0]
    assert area["data"]["observed_at"] == body["observed_at"]
    assert body["areas"][0]["forecast"] == []
    assert "행사장 안 혼잡과 다를 수 있어요" in body["notices"]
    assert "출처 서울특별시 · 2026년 서울시 인구데이터 (OA-21778)" in body["notices"]
    label = "축제 근처 지역 혼잡(서울시 실시간 도시데이터)"
    is_estimate = fixture == "replacement"
    assert body["is_estimate"] is is_estimate and area["is_estimate"] is is_estimate
    assert any(label in notice for notice in body["notices"]) is not is_estimate
    assert any("최근 4주 같은 시간대 평균이에요" in notice for notice in body["notices"]) is is_estimate


@pytest.mark.parametrize(
    ("changes", "reason"), [
        ({"region_code": "BUSAN"}, "outside_seoul"),
        ({"lat": None}, "missing_coordinates"),
        ({"lat": 37.7, "lng": 127.1}, "no_nearby_areas"),
    ],
)
def test_P1_unsupported_without_provider_call(monkeypatch, changes, reason) -> None:
    festival = festivals[_FESTIVAL].model_copy(update=changes)
    monkeypatch.setattr(seoul_crowd, "find_festival", lambda _: festival)
    service = _service(_unexpected)
    response = asyncio.run(service.get_crowd(_FESTIVAL))
    assert response.status == "unsupported" and response.unsupported_reason == reason
    assert not response.areas and not response.nearby_areas and response.error is None
    assert response.coverage.supported is (reason != "outside_seoul")


@pytest.mark.parametrize(
    ("fault", "retryable"), [
        ("body_error", True), ("body_key_error", False), ("gateway_INFO-100", False),
        ("gateway_INFO-200", False), ("mismatch", True),
        ("invalid_payload", True), ("bad_json", True), ("http_503", True),
        ("http_429", True), ("http_403", False), ("timeout", True),
        ("future", True), ("bad_replacement_flag", True), ("bad_population", True),
    ],
)
def test_P2_failures_keep_source_error_and_are_not_cached(fault, retryable) -> None:
    calls = 0

    def send(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        if calls > 1:
            return _observed(request)
        if fault.startswith("http_"):
            return httpx2.Response(int(fault.split("_")[1]))
        if fault == "timeout":
            raise httpx2.ReadTimeout(f"timeout {request.url}", request=request)
        if fault == "body_error":
            return httpx2.Response(200, json=_body("unknown_area"))
        if fault == "body_key_error":
            return httpx2.Response(200, json={"RESULT": {"RESULT.CODE": "INFO-100"}})
        if fault.startswith("gateway_"):
            return httpx2.Response(200, json={"RESULT": {"CODE": fault.removeprefix("gateway_")}})
        if fault == "bad_json":
            return httpx2.Response(200, content=b"{invalid")
        if fault == "invalid_payload":
            return httpx2.Response(200, json={"RESULT": {"RESULT.CODE": "INFO-000"}})
        if fault == "mismatch":
            return httpx2.Response(200, json=_reading_for("POI999"))

        body = _body("observed")
        item = body["SeoulRtd.citydata_ppltn"][0]
        if fault == "future":
            item["PPLTN_TIME"] = "2026-11-19 18:00"
        elif fault == "bad_replacement_flag":
            item["REPLACE_YN"] = "?"
        elif fault == "bad_population":
            item["AREA_PPLTN_MIN"] = "50001"
        return httpx2.Response(200, json=body)

    async def check() -> None:
        service = _service(send)
        first = await service.get_crowd(_FESTIVAL)
        assert first.status == "unavailable"
        assert first.error.code == "SOURCE_RESULT_ERROR" and first.error.retryable is retryable
        assert first.areas == [] and first.observed_at is None
        assert first.nearby_areas[0].status == "unavailable"
        assert first.nearby_areas[0].error == first.error
        assert _TEST_KEY not in first.model_dump_json()
        assert (await service.get_crowd(_FESTIVAL)).status == "ok"
        assert calls == 2

    asyncio.run(check())


def test_P2_total_timeout(monkeypatch) -> None:
    monkeypatch.setattr(seoul_citydata, "_TIMEOUT_SECONDS", 0.02)

    async def send(_: httpx2.Request) -> httpx2.Response:
        await asyncio.Event().wait()
        pytest.fail("제한 시간 안에 취소되어야 합니다.")

    response = asyncio.run(_service(send).get_crowd(_FESTIVAL))
    assert response.status == "unavailable" and "시간이 초과" in response.error.message


def test_P2_key_does_not_escape_through_logs_or_public_messages(caplog) -> None:
    def send(request: httpx2.Request) -> httpx2.Response:
        logging.getLogger("httpx2").info("request %s", request.url)
        body = _body("observed")
        body["SeoulRtd.citydata_ppltn"][0]["AREA_CONGEST_MSG"] += _TEST_KEY
        return httpx2.Response(200, json=body)

    with caplog.at_level(logging.INFO):
        response = asyncio.run(_service(send).get_crowd(_FESTIVAL))
    assert response.status == "ok"
    assert "request http" in caplog.text
    assert _TEST_KEY not in caplog.text
    assert _TEST_KEY not in response.model_dump_json()


def test_P3_partial_failure_preserves_order_and_uses_nearest_success(monkeypatch) -> None:
    codes = ["POI009", "POI008", "POI007", "POI006"]
    areas = tuple(_area(code, index * 0.001) for index, code in enumerate(codes))
    _set_areas(monkeypatch, areas[::-1])
    calls = set()

    def send(request: httpx2.Request) -> httpx2.Response:
        code = _request_area(request)
        calls.add(code)
        return httpx2.Response(503) if code == codes[0] else _observed(request)

    response = asyncio.run(_service(send).get_crowd(_FESTIVAL))
    assert [area.area_code for area in response.nearby_areas] == codes[:3]
    assert [area.status for area in response.nearby_areas] == ["unavailable", "ok", "ok"]
    assert calls == set(codes[:3])
    assert response.status == "ok" and response.error is None
    assert response.areas[0].area_code == codes[1]
    assert response.areas[0].relation_type == "adjacent"


@pytest.mark.parametrize("now_at_start", [_NOW, _NOW.replace(tzinfo=None)], ids=["kst", "naive"])
def test_P4_success_cache_expires_at_sixty_seconds_and_rechecks_stale(
    now_at_start: datetime,
) -> None:
    calls = 0
    tick = 0.0
    now = now_at_start

    def send(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return _observed(request)

    async def check() -> None:
        nonlocal tick, now
        service = _service(send, now=lambda: now, clock=lambda: tick)
        first = await service.get_crowd(_FESTIVAL)
        now += timedelta(minutes=14)
        tick = 59.99
        assert (await service.get_crowd(_FESTIVAL)).status == "ok"
        now += timedelta(seconds=1)
        response = await service.get_crowd(_FESTIVAL)
        assert response.status == "stale" and response.nearby_areas[0].status == "stale"
        assert response.observed_at == first.observed_at
        assert calls == 1
        tick = 60.0
        await service.get_crowd(_FESTIVAL)
        assert calls == 2

    asyncio.run(check())


@pytest.mark.parametrize("available", [True, False])
def test_P3_positive_distance_below_rounding_threshold_stays_adjacent(
    monkeypatch: pytest.MonkeyPatch, available: bool,
) -> None:
    # 축제 위치보다 0.02m가량 북쪽에서 시작하는 구역.
    area = _area("POI009", offset=0.0001002)
    _set_areas(monkeypatch, (area,))

    def send(request: httpx2.Request) -> httpx2.Response:
        return _observed(request) if available else httpx2.Response(503)

    response = asyncio.run(_service(send).get_crowd(_FESTIVAL))
    (nearby,) = response.nearby_areas
    assert nearby.distance_m == 0.1
    if available:
        assert nearby.data.relation_type == "adjacent"
        assert any(" · 0.1m · " in notice for notice in response.notices)
    else:
        assert nearby.status == "unavailable"


def test_P4_concurrent_same_area_merges_across_festivals(monkeypatch) -> None:
    festival = festivals[_FESTIVAL]
    monkeypatch.setattr(seoul_crowd, "find_festival", lambda _: festival)

    async def check() -> None:
        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def send(request: httpx2.Request) -> httpx2.Response:
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return _observed(request)

        service = _service(send)
        first = asyncio.create_task(service.get_crowd(_FESTIVAL))
        await started.wait()
        second = asyncio.create_task(service.get_crowd("fst_000002"))
        # 두 번째 요청이 진행 중인 공급원 작업에 실제로 합류하는지 확인한다.
        original = asyncio.shield
        joined = asyncio.Event()

        def watch(task):
            joined.set()
            return original(task)

        monkeypatch.setattr(asyncio, "shield", watch)
        async with asyncio.timeout(1):
            await joined.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        release.set()
        assert (await second).status == "ok"
        assert calls == 1

    asyncio.run(check())


def test_P4_quota_persists_counts_failures_and_resets_at_kst_midnight(monkeypatch) -> None:
    monkeypatch.setenv("CROWD_SEOUL_DAILY_LIMIT", "1")
    now = _NOW.replace(hour=23, minute=59)
    calls = 0

    def send(_: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(503)

    async def check() -> None:
        nonlocal now
        first = await _service(send, now=lambda: now).get_crowd(_FESTIVAL)
        assert first.status == "unavailable" and first.error.retryable
        service = _service(send, now=lambda: now)
        second = await service.get_crowd(_FESTIVAL)
        assert second.status == "unavailable" and not second.error.retryable
        assert "한도를 다 썼어요" in second.error.message
        assert calls == 1
        now += timedelta(minutes=1)
        await service.get_crowd(_FESTIVAL)
        assert calls == 2

    asyncio.run(check())


@pytest.mark.parametrize(
    "state", [[], {"date": _NOW.date().isoformat(), "counts": []}], ids=["state", "counts"],
)
def test_P4_corrupt_quota_returns_unavailable_without_provider_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: object,
) -> None:
    path = tmp_path / "corrupt-quota.json"
    monkeypatch.setenv("CROWD_QUOTA_FILE", str(path))
    original = json.dumps(state)
    path.write_text(original, encoding="utf-8")
    service = _service(_unexpected)

    with pytest.raises(ValueError):
        service._quota.status()
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: service)
    monkeypatch.setenv("CROWD_PROVIDER", "real")
    with TestClient(app) as client:
        response = client.get(_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["error"] == {
        "code": "SOURCE_RESULT_ERROR",
        "message": "서울시 혼잡 조회 한도를 확인할 수 없어요.",
        "retryable": False,
    }
    assert path.read_text(encoding="utf-8") == original


def test_P5_missing_real_key_returns_unavailable_without_using_quota(monkeypatch) -> None:
    monkeypatch.delenv("SEOUL_OPEN_API_KEY")
    service = _service(_unexpected)
    response = asyncio.run(service.get_crowd(_FESTIVAL))
    assert response.is_mock is False and response.status == "unavailable"
    assert response.error.code == "SOURCE_RESULT_ERROR" and not response.error.retryable
    assert not service._quota._path.exists()
