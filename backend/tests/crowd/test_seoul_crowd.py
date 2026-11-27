import asyncio
import json
import logging
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.mocks.store import festivals
from api.providers import seoul_citydata
from api.providers.seoul_citydata import SeoulCityData
from api.schemas.festivals import FestivalDetail
from api.services import mock_festival_info, seoul_crowd, seoul_crowd_mapping
from api.services.seoul_areas import SeoulArea, SeoulAreaCatalog, load_catalog
from api.services.seoul_crowd import SeoulCrowdService

_FESTIVAL = "fst_000001"
_URL = f"/api/v1/festivals/{_FESTIVAL}/crowd"
_NOW = datetime.fromisoformat("2026-11-19T17:26:00+09:00")
_REPLACEMENT_NOW = datetime.fromisoformat("2026-11-23T15:55:00+09:00")
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


def _mapping(festival: FestivalDetail, decisions: dict[str, bool]) -> dict:
    return festival.model_dump(include={"festival_id", "region_code", "lat", "lng", "venue_name", "address"}) | {
        "candidates": [{"area_code": code, "approved": approved} for code, approved in decisions.items()]
    }


@pytest.fixture
def write_mappings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Callable[..., None]]:
    path = tmp_path / "mapping.json"
    monkeypatch.setattr(seoul_crowd_mapping, "_MAPPING_PATH", path)

    def write(*entries: dict) -> None:
        path.write_text(json.dumps({"schema_version": 1, "festivals": entries}), encoding="utf-8")
        seoul_crowd_mapping._load_mappings.cache_clear()

    yield write
    seoul_crowd_mapping._load_mappings.cache_clear()


@pytest.fixture(autouse=True)
def defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write_mappings: Callable[..., None]) -> None:
    monkeypatch.setenv("SEOUL_OPEN_API_KEY", _TEST_KEY)
    monkeypatch.setenv("CROWD_QUOTA_FILE", str(tmp_path / "crowd.json"))
    monkeypatch.delenv("CROWD_SEOUL_DAILY_LIMIT", raising=False)
    monkeypatch.delenv("CROWD_PROVIDER", raising=False)
    monkeypatch.setenv("FESTIVAL_DATA", "mock")
    _set_areas(monkeypatch, (_area("POI009"),))
    write_mappings(_mapping(festivals[_FESTIVAL], {"POI009": True}))


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
    if status in {"ok", "stale"}:
        assert any(notice.startswith("주변 지역 혼잡(모의 데이터)") for notice in response.json()["notices"])


def test_P2_P3_real_headers_legacy_keys_and_labels(monkeypatch) -> None:
    service = _service(_observed)
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
    assert body["is_estimate"] is False and area["is_estimate"] is False
    assert any(notice.startswith("주변 지역 혼잡(서울시 실시간 도시데이터)") for notice in body["notices"])


def test_P2_replacement_values_are_neither_returned_nor_cached(monkeypatch) -> None:
    calls = 0

    def send(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        return httpx2.Response(200, json=_body("replacement")) if calls == 1 else _observed(request)

    service = _service(send, now=lambda: _REPLACEMENT_NOW)
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: service)
    monkeypatch.setenv("CROWD_PROVIDER", "real")
    with TestClient(app) as client:
        first = client.get(_URL)
        second = client.get(_URL)
    assert first.status_code == 200
    body = first.json()
    assert body["status"] == "unavailable" and body["error"]["retryable"]
    assert body["areas"] == [] and body["observed_at"] is None and body["is_estimate"] is None
    assert [area["status"] for area in body["nearby_areas"]] == ["unavailable"]
    (area,) = body["nearby_areas"]
    assert area["data"] is None and area["is_estimate"] is None
    assert "4주" not in first.text
    assert second.json()["status"] == "stale" and calls == 2


@pytest.mark.parametrize(
    ("changes", "reason"), [
        ({"region_code": "BUSAN"}, "outside_seoul"),
        ({"lat": None}, "missing_coordinates"),
        ({"lat": 37.7, "lng": 127.1}, "no_nearby_areas"),
    ],
)
def test_P1_unsupported_without_provider_call(monkeypatch, changes, reason) -> None:
    festival = festivals[_FESTIVAL].model_copy(update=changes)
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=festival))
    service = _service(_unexpected)
    response = asyncio.run(service.get_crowd(_FESTIVAL))
    assert response.status == "unsupported" and response.unsupported_reason == reason
    assert not response.areas and not response.nearby_areas and response.error is None
    assert response.coverage.supported is (reason != "outside_seoul")
    assert not service._quota._path.exists()


def test_P1_approved_area_outside_radius_keeps_reason(monkeypatch) -> None:
    _set_areas(monkeypatch, (_area("POI009", offset=0.05), _area("POI008")))
    service = _service(_unexpected)
    response = asyncio.run(service.get_crowd(_FESTIVAL))
    assert response.status == "unsupported" and response.unsupported_reason == "no_nearby_areas"
    assert not service._quota._path.exists()


def test_P1_manual_mapping_survives_resync_text_and_small_coord_drift(monkeypatch) -> None:
    # DB 재수집으로 주소·장소명이 바뀌거나 좌표가 100m 이내(~40m)로 움직여도 기존 승인 매핑 유지
    base = festivals[_FESTIVAL]
    resynced = base.model_copy(update={
        "address": "서울특별시 중구 태평로1가 1 (재수집 표기 변경)",
        "venue_name": "광화문 일대 (재수집)",
        "lat": base.lat + 0.00035,  # 약 39m
    })
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=resynced))
    response = asyncio.run(_service(_observed).get_crowd(_FESTIVAL))
    assert response.status == "ok"
    assert [area.area_code for area in response.nearby_areas] == ["POI009"]

    # 좌표가 100m보다 크게(약 200m) 이동하면 기존 수동 승인 매핑 무효화 + 관측 범위 밖
    relocated = base.model_copy(update={"lat": base.lat + 0.002})
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=relocated))
    far_response = asyncio.run(_service(_unexpected).get_crowd(_FESTIVAL))
    assert far_response.status == "unsupported"
    assert far_response.unsupported_reason == "no_nearby_areas"


def test_P1_three_tier_classification_on_official_catalog(monkeypatch) -> None:
    mapping_path = Path(__file__).resolve().parents[2] / "api" / "data" / "seoul_crowd_mapping.json"
    monkeypatch.setattr(seoul_crowd_mapping, "_MAPPING_PATH", mapping_path)
    seoul_crowd_mapping._load_mappings.cache_clear()
    official_catalog = load_catalog()
    monkeypatch.setattr(seoul_crowd, "load_catalog", lambda: official_catalog)
    saved = json.loads(mapping_path.read_text(encoding="utf-8"))
    location_fields = {"festival_id", "region_code", "lat", "lng", "venue_name", "address"}

    # 1) 경계 근처(내부 <=25m 또는 외부 <=25m) 미승인 축제 -> 검토 대상(no_approved_mapping), 공급원·할당량 미사용
    near_in_entry = next(
        entry for entry in saved["festivals"]
        if entry["decision"] == "review_required" and entry["reasons"] == ["near_boundary"]
    )
    near_out_entry = next(
        entry for entry in saved["festivals"]
        if entry["decision"] == "unsupported"
        and entry.get("nearest_excluded_area")
        and entry["nearest_excluded_area"]["boundary_distance_m"] <= 25
    )
    for entry in (near_in_entry, near_out_entry):
        festival = festivals[_FESTIVAL].model_copy(update={key: entry[key] for key in location_fields})
        monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=festival))
        service = _service(_unexpected)
        res = asyncio.run(service.get_crowd(festival.festival_id))
        assert res.status == "unsupported" and res.unsupported_reason == "no_approved_mapping"
        assert not service._quota._path.exists()

    # 2) 관측 범위 밖(외부 >25m) 서울 축제 -> 관측 범위 밖(no_nearby_areas), 공급원·할당량 미사용
    outside_entry = next(
        entry for entry in saved["festivals"]
        if entry["decision"] == "unsupported"
        and entry.get("nearest_excluded_area")
        and entry["nearest_excluded_area"]["boundary_distance_m"] > 25
    )
    outside_festival = festivals[_FESTIVAL].model_copy(update={key: outside_entry[key] for key in location_fields})
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=outside_festival))
    out_service = _service(_unexpected)
    out_res = asyncio.run(out_service.get_crowd(outside_festival.festival_id))
    assert out_res.status == "unsupported" and out_res.unsupported_reason == "no_nearby_areas"
    assert not out_service._quota._path.exists()

    # 3) 관측 구역 안에 확실히 포함(>25m)된 미승인/신규 축제 -> 자동 승인 후 실제 혼잡도 반환
    interior_entry = next(
        entry for entry in saved["festivals"]
        if entry["decision"] == "candidate" and not any(area["approved"] for area in entry["candidates"])
    )
    interior_festival = festivals[_FESTIVAL].model_copy(
        update={key: interior_entry[key] for key in location_fields} | {"festival_id": "fst_new_seoul_01"}
    )
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=interior_festival))
    auto_response = asyncio.run(_service(_observed).get_crowd(interior_festival.festival_id))
    assert auto_response.status == "ok"
    assert auto_response.areas[0].area_code == interior_entry["candidates"][0]["area_code"]
    assert auto_response.areas[0].relation_type == "contains"

    # 4) 수동 승인 축제(서울빛초롱축제)는 재수집으로 주소·장소명이 바뀌어도 경계 근처 승인 구역(POI003)까지 유지
    lantern_entry = next(entry for entry in saved["festivals"] if entry["name"] == "서울빛초롱축제")
    lantern_resynced = festivals[_FESTIVAL].model_copy(
        update={key: lantern_entry[key] for key in location_fields}
        | {"address": "서울 중구 태평로1가 1", "venue_name": "청계천 일대"}
    )
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(return_value=lantern_resynced))
    lantern_res = asyncio.run(_service(_observed).get_crowd(lantern_resynced.festival_id))
    assert lantern_res.status == "ok"
    assert {area.area_code for area in lantern_res.nearby_areas} == {"POI009", "POI130", "POI003"}


def test_P1_string_approval_does_not_enable_real_lookup() -> None:
    path = seoul_crowd_mapping._MAPPING_PATH
    body = path.read_text(encoding="utf-8").replace('"approved": true', '"approved": "true"')
    path.write_text(body, encoding="utf-8")
    service = _service(_unexpected)
    response = asyncio.run(service.get_crowd(_FESTIVAL))
    assert response.status == "unsupported" and response.unsupported_reason == "no_approved_mapping"
    assert not service._quota._path.exists()


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


@pytest.mark.parametrize("failure", ["http_error", "replacement"])
def test_P3_partial_failure_preserves_order_and_uses_nearest_success(monkeypatch, write_mappings, failure) -> None:
    codes = ["POI009", "POI008", "POI007", "POI006"]
    areas = tuple(_area(code, index * 0.001) for index, code in enumerate(codes))
    unapproved = _area("POI005")
    _set_areas(monkeypatch, areas[::-1] + (unapproved,))
    write_mappings(_mapping(festivals[_FESTIVAL], dict.fromkeys(codes, True) | {unapproved.code: False}))
    calls = set()

    def send(request: httpx2.Request) -> httpx2.Response:
        code = _request_area(request)
        calls.add(code)
        if code != codes[0]:
            return _observed(request)
        if failure == "replacement":
            return httpx2.Response(200, json=_reading_for(code, "replacement"))
        return httpx2.Response(503)

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


def test_P4_concurrent_same_area_merges_across_festivals(monkeypatch, write_mappings) -> None:
    first_festival = festivals[_FESTIVAL]
    second_festival = first_festival.model_copy(update={"festival_id": "fst_000002"})
    by_id = {festival.festival_id: festival for festival in (first_festival, second_festival)}
    monkeypatch.setattr(seoul_crowd, "find_festival", AsyncMock(side_effect=by_id.get))
    write_mappings(*(_mapping(festival, {"POI009": True}) for festival in by_id.values()))

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


def _assert_seoul_geo(center: dict, boundary: list) -> None:
    assert center.keys() == {"lat", "lng"}
    assert 37.0 <= center["lat"] <= 38.0 and 126.0 <= center["lng"] <= 128.0
    assert isinstance(boundary, list) and len(boundary) >= 1
    for ring in boundary:
        assert isinstance(ring, list) and len(ring) >= 4
        assert ring[0] == ring[-1]
        for point in ring:
            assert point.keys() == {"lat", "lng"}
            assert 37.0 <= point["lat"] <= 38.0 and 126.0 <= point["lng"] <= 128.0


def test_real_crowd_returns_official_center_and_boundary_on_areas_and_nearby(
    monkeypatch: pytest.MonkeyPatch, write_mappings: Callable[..., None],
) -> None:
    official_catalog = load_catalog()
    monkeypatch.setattr(seoul_crowd, "load_catalog", lambda: official_catalog)
    write_mappings(_mapping(festivals[_FESTIVAL], {"POI009": True, "POI130": True}))

    def send(request: httpx2.Request) -> httpx2.Response:
        code = _request_area(request)
        if code == "POI130":
            return httpx2.Response(503)
        return _observed(request)

    service = _service(send)
    monkeypatch.setattr(seoul_crowd, "get_service", lambda: service)
    monkeypatch.setenv("CROWD_PROVIDER", "real")

    with TestClient(app) as client:
        response = client.get(_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is False and body["status"] == "ok"
    assert len(body["areas"]) == 1
    assert len(body["nearby_areas"]) == 2

    primary = body["areas"][0]
    poi009_nearby, poi130_nearby = body["nearby_areas"]

    # 기존 필드 유지 확인
    assert primary["area_code"] == "POI009"
    assert primary["area_name"] == "광화문·덕수궁"
    assert primary["relation_type"] == "contains"
    assert primary["congest_level"] == "보통"
    assert primary["congest_color"] == "yellow"
    assert primary["population_min"] == 48000
    assert primary["population_max"] == 50000
    assert primary["observed_at"] == body["observed_at"]
    assert primary["forecast"] == []

    # areas[0], nearby_areas[0], nearby_areas[0].data 모두 공식 경계·중심 포함
    assert primary["center"] == {"lat": 37.5709305, "lng": 126.9771863}
    assert len(primary["boundary"]) == 1 and len(primary["boundary"][0]) == 30
    _assert_seoul_geo(primary["center"], primary["boundary"])
    assert poi009_nearby["data"] == primary
    assert poi009_nearby["center"] == primary["center"]
    assert poi009_nearby["boundary"] == primary["boundary"]

    # 조회 실패(unavailable)한 인접 구역도 공식 center·boundary를 유지
    assert poi130_nearby["area_code"] == "POI130"
    assert poi130_nearby["status"] == "unavailable" and poi130_nearby["data"] is None
    _assert_seoul_geo(poi130_nearby["center"], poi130_nearby["boundary"])


def test_real_crowd_multipolygon_and_missing_geometry(monkeypatch: pytest.MonkeyPatch) -> None:
    festival = festivals[_FESTIVAL]
    lat, lng = festival.lat, festival.lng
    outer = [
        (lat - 0.001, lng - 0.001), (lat + 0.001, lng - 0.001),
        (lat + 0.001, lng + 0.001), (lat - 0.001, lng + 0.001),
        (lat - 0.001, lng - 0.001),
    ]
    hole = [
        (lat - 0.0002, lng - 0.0002), (lat + 0.0002, lng - 0.0002),
        (lat + 0.0002, lng + 0.0002), (lat - 0.0002, lng + 0.0002),
        (lat - 0.0002, lng - 0.0002),
    ]
    second = [
        (lat + 0.002, lng + 0.002), (lat + 0.003, lng + 0.002),
        (lat + 0.003, lng + 0.003), (lat + 0.002, lng + 0.003),
        (lat + 0.002, lng + 0.002),
    ]
    multi_area = SeoulArea("POI009", "멀티 구역", [[outer, hole], [second]], centroid=(lat, lng))
    _set_areas(monkeypatch, (multi_area,))
    service = _service(_observed)

    response = asyncio.run(service.get_crowd(_FESTIVAL))
    dumped = response.model_dump(mode="json")
    assert dumped["areas"][0]["center"] == {"lat": lat, "lng": lng}
    assert len(dumped["areas"][0]["boundary"]) == 3
    assert dumped["areas"][0]["boundary"][0][0] == {"lat": outer[0][0], "lng": outer[0][1]}
    assert dumped["areas"][0]["boundary"][1][0] == {"lat": hole[0][0], "lng": hole[0][1]}
    assert dumped["areas"][0]["boundary"][2][0] == {"lat": second[0][0], "lng": second[0][1]}
    assert dumped["nearby_areas"][0]["boundary"] == dumped["areas"][0]["boundary"]

    # 도형이 없는 구역은 좌표를 만들어내지 않고 center·boundary 모두 null 반환
    empty_area = SeoulArea("POI999", "도형 없음", [], centroid=(lat, lng))
    empty_result = asyncio.run(service._area_result(empty_area, 0.0)).model_dump(mode="json")
    assert empty_result["center"] is None and empty_result["boundary"] is None
    assert empty_result["data"]["center"] is None and empty_result["data"]["boundary"] is None


def test_mock_crowd_returns_catalog_geometry_and_null_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(app) as client:
        response = client.get(_URL)
    assert response.status_code == 200
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body.keys() == _LEGACY_KEYS
    (area,) = body["areas"]
    assert area["area_code"] == "POI009"
    assert area["center"] == {"lat": 37.5709305, "lng": 126.9771863}
    assert len(area["boundary"]) == 1 and len(area["boundary"][0]) == 30
    _assert_seoul_geo(area["center"], area["boundary"])

    # 카탈로그에 없는 구역은 null 반환(좌표 생성 금지)
    empty_catalog = SeoulAreaCatalog((), load_catalog().source_url)
    monkeypatch.setattr(mock_festival_info, "load_catalog", lambda: empty_catalog)
    with TestClient(app) as client:
        missing_geo = client.get(_URL).json()
    (missing_area,) = missing_geo["areas"]
    assert missing_area["area_code"] == "POI009"
    assert missing_area["center"] is None
    assert missing_area["boundary"] is None
