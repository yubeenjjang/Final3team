import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from api.main import app
from api.providers import festival_source, kma_weather, transit_arrivals, visit_forecast
from api.providers.festival_source import FestivalSource
from api.providers.route_base import KST
from api.repositories import festival_info as repository
from api.services import real_festival_info

_NOW = datetime(2026, 11, 19, 17, 23, 30, tzinfo=KST)
_MOCK_KEY = "fixture+private/test="
_FIXTURES = Path(__file__).with_name("fixtures")
_BASE = "/api/v1/festivals"


def _load(name):
    return json.loads((_FIXTURES / (name + ".json")).read_text())


def _url(endpoint, festival="fst_000001"):
    return f"{_BASE}/{festival}/{endpoint}"


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("FESTIVAL_INFO_QUOTA_FILE", str(tmp_path / "quota.json"))
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", "fixture%2Bprivate%2Ftest%3D")
    monkeypatch.setenv("SEOUL_SUBWAY_API_KEY", _MOCK_KEY)
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.delenv("VISIT_FORECAST_STORE", raising=False)
    monkeypatch.delenv("VISIT_FORECAST_MAPPING_FILE", raising=False)
    monkeypatch.setattr(festival_source, "_RETRY_DELAY_S", 0)
    now = [_NOW]
    clock = [0.0]
    calls = []

    def configure(routes):
        def handler(request):
            name = request.url.path.split("/")[-1]
            if "realtimeStationArrival" in request.url.path:
                name = "subway"
            calls.append((name, dict(request.url.params)))
            if name not in routes:
                pytest.fail(f"예상하지 않은 공급원 호출 {name}")
            fixture = routes[name]
            if callable(fixture):
                return fixture(request)
            return httpx2.Response(200, json=_load(fixture))

        service = real_festival_info.FestivalInfoService(FestivalSource(
            transport=httpx2.MockTransport(handler), now=lambda: now[0], clock=lambda: clock[0],
        ))
        monkeypatch.setattr(real_festival_info, "get_service", lambda: service)
        return calls, now, clock

    return configure


def test_weather_grid_and_real_endpoint_cache(setup, monkeypatch):
    assert kma_weather.weather_grid(37.5759, 126.9768).model_dump() == {"nx": 60, "ny": 127}
    assert kma_weather.weather_grid(35.1151, 129.0414).model_dump() == {"nx": 97, "ny": 74}
    monkeypatch.setenv("WEATHER_PROVIDER", "real")
    calls, _, clock = setup({
        "getUltraSrtNcst": "kma_current",
        "getVilageFcst": "kma_forecast_synthetic",
    })
    with TestClient(app) as client:
        response = client.get(_url("weather"))
        assert "X-Mock" not in response.headers
        body = response.json()
        assert body["status"] == "ok"
        assert body["is_mock"] is False
        data = body["data"]
        assert body["observed_at"] == data["observed_at"] == "2026-11-19T16:00:00+09:00"
        assert data["temperature_c"] == 3.6
        assert data["precipitation_mm"] == 0
        assert data["forecast"] == {
            "status": "ok", "issued_at": "2026-11-19T17:00:00+09:00",
            "items": [{
                "forecast_at": "2026-11-19T18:00:00+09:00", "temperature_c": 10,
                "precipitation_mm": 1.7, "precipitation_type": "rain",
            }],
        }
        clock[0] = 599
        assert client.get(_url("weather")).json() == body
        assert [name for name, _ in calls] == ["getUltraSrtNcst", "getVilageFcst"]
        assert [call["base_time"] for _, call in calls] == ["1600", "1700"]
        assert calls[0][1]["serviceKey"] == _MOCK_KEY
        clock[0] = 600
        assert client.get(_url("weather")).json() == body
        assert len(calls) == 4


@pytest.mark.parametrize("case, expected_calls, code, retryable", [
    ("key", 1, "SOURCE_RESULT_ERROR", False),
    ("empty", 1, "SOURCE_RESULT_ERROR", False),
    ("timeout", 2, "SOURCE_HTTP_ERROR", True),
    ("quota", 0, "SOURCE_RESULT_ERROR", False),
    ("xml_quota", 1, "SOURCE_RESULT_ERROR", False),
    ("http_retry", 2, "SOURCE_HTTP_ERROR", True),
    ("http_forbidden", 1, "SOURCE_HTTP_ERROR", False),
])
def test_weather_failures_do_not_log_or_return_key(setup, monkeypatch, caplog, case, expected_calls, code, retryable):
    monkeypatch.setenv("WEATHER_PROVIDER", "real")
    monkeypatch.setenv("KMA_DAILY_LIMIT", "0" if case == "quota" else "10000")
    caplog.set_level(logging.DEBUG)

    def respond(request):
        logging.getLogger("httpcore2.http11").debug("url %s", request.url)
        logging.getLogger("httpx2").debug("raw %s", request.url.params["serviceKey"])
        if case == "timeout":
            raise httpx2.ReadTimeout(str(request.url), request=request)
        if case == "http_retry":
            return httpx2.Response(429, headers={"Retry-After": "0"}, text=str(request.url))
        if case == "http_forbidden":
            return httpx2.Response(403, text=str(request.url))
        if case == "xml_quota":
            return httpx2.Response(200, text=(
                "<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>22</returnReasonCode>"
                "</cmmMsgHeader></OpenAPI_ServiceResponse>"
            ))
        payload = _load("tago_empty" if case == "empty" else "data_key_error")
        payload["sensitive"] = _MOCK_KEY
        return httpx2.Response(200, json=payload)

    calls, _, _ = setup({"getUltraSrtNcst": respond})
    with TestClient(app) as client:
        result = client.get(_url("weather"))
    assert result.status_code == 200
    assert result.json()["status"] == "unavailable"
    assert result.json()["error"]["code"] == code
    assert result.json()["error"]["retryable"] is retryable
    assert result.json()["data"] is None
    assert len(calls) == expected_calls
    for key in (_MOCK_KEY, "fixture%2Bprivate%2Ftest%3D"):
        assert key not in caplog.text
        assert key not in result.text


def test_weather_stale_and_partial_forecast_failure(setup, monkeypatch):
    monkeypatch.setenv("WEATHER_PROVIDER", "real")
    calls, now, _ = setup({"getUltraSrtNcst": "kma_current", "getVilageFcst": "data_key_error"})
    now[0] = _NOW + timedelta(hours=1)
    with TestClient(app) as client:
        body = client.get(_url("weather")).json()
        assert body["status"] == "stale"
        assert body["observed_at"] == "2026-11-19T16:00:00+09:00"
        assert body["data"]["forecast"]["status"] == "unavailable"
        assert client.get(_url("weather", "fst_000006")).json()["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    assert len(calls) == 2


def _station(kind, name, lat, lng, region, source, ref, node):
    return repository.FacilityStation(kind, f"sta_{node}", name, lat, lng, region, source, node, ref)


def test_subway_preserves_zero_eta_message_and_unsupported(setup, monkeypatch):
    monkeypatch.setenv("TRANSIT_PROVIDER", "real")
    station = _station("subway", "서울역", 37.5758, 126.9768, "SEOUL", "subway", None, "1")
    calls, now, _ = setup({"subway": "subway"})
    monkeypatch.setattr(repository, "nearby_facilities", lambda *args: [station])
    with TestClient(app) as client:
        resp = client.get(_url("transit"), params={"mode": "subway"})
        assert "X-Mock" not in resp.headers
        body = resp.json()
        assert body["status"] == "ok"
        arrival = body["stations"][0]["arrivals"][0]
        # 공급원에 ETA 0초가 있어도 서울역에서 출발 중이라는 문구를 유지한다.
        assert (arrival["eta_s"], arrival["message"], arrival["direction"]) == (0, "서울 출발", "상행")
        now[0] += timedelta(minutes=2)
        assert client.get(_url("transit"), params={"mode": "subway"}).json()["status"] == "stale"
        unsupported = client.get(_url("transit", "fst_000003"), params={"mode": "subway"}).json()
        assert unsupported["status"] == "unsupported"
        assert unsupported["coverage"] == {"scope": "seoul_only", "region_code": "BUSAN", "supported": False}
        assert client.get(_url("transit"), params={"limit": 11}).status_code == 422
    assert [call[0] for call in calls] == ["subway"]


def test_subway_path_key_is_hidden_on_body_error(setup, monkeypatch, caplog):
    monkeypatch.setenv("TRANSIT_PROVIDER", "real")
    station = _station("subway", "서울역", 37.5758, 126.9768, "SEOUL", "subway", None, "1")
    monkeypatch.setattr(repository, "nearby_facilities", lambda *args: [station])
    caplog.set_level(logging.DEBUG)

    def respond(request):
        logging.getLogger("httpx2").debug("path %s", request.url)
        return httpx2.Response(200, json=_load("subway_key_error"))

    calls, _, _ = setup({"subway": respond})
    with TestClient(app) as client:
        response = client.get(_url("transit"), params={"mode": "subway"})
        assert response.json()["error"]["retryable"] is False
        assert response.json()["stations"][0]["status"] == "unavailable"
    assert len(calls) == 1
    assert _MOCK_KEY not in response.text and _MOCK_KEY not in caplog.text
    assert "fixture%2Bprivate%2Ftest%3D" not in caplog.text


def test_tago_retries_matches_city_and_uses_radius_and_limit(setup, monkeypatch):
    monkeypatch.setenv("TRANSIT_PROVIDER", "real")
    station = _station("bus", "서면역", 35.1004, 129.0337, "BUSAN", "tago_stop", None, "BSB164680201")
    far = _station("bus", "먼정류장", 35.1199, 129.0337, "BUSAN", "tago_stop", None, "far")
    station2 = _station("bus", "가까운정류장", 35.105, 129.0337, "BUSAN", "tago_stop", None, "other")
    monkeypatch.setattr(repository, "nearby_facilities", lambda *args: [far, station2, station])
    count = 0

    def arrival(request):
        nonlocal count
        count += 1
        assert request.url.params["cityCode"] == "21" and request.url.params["nodeId"] == station.source_item_id
        return httpx2.Response(200, json=_load("tago_retry_synthetic" if count == 1 else "tago_arrivals"))

    calls, _, _ = setup({
        "getCrdntPrxmtSttnList": "tago_stop", "getSttnAcctoArvlPrearngeInfoList": arrival,
    })
    with TestClient(app) as client:
        response = client.get(_url("transit", "fst_000003"), params={"mode": "bus", "radius_m": 1000, "limit": 1})
        body = response.json()
        assert body["status"] == "ok"
        (item,) = body["stations"]
        assert item["station_id"] == station.station_id
        assert item["arrivals"][0] == {
            "line": "부산진구12", "remaining_stops": 0, "eta_s": 8, "direction": None,
            "message": None, "crowding": None,
        }
    assert len(calls) == 3


@pytest.mark.parametrize(("fixture", "expected"), [("tago_empty", "ok"), ("data_key_error", "unavailable")])
def test_tago_empty_and_body_error(setup, monkeypatch, fixture, expected):
    monkeypatch.setenv("TRANSIT_PROVIDER", "real")
    station = _station("bus", "부산역", 35.1004, 129.0337, "BUSAN", "tago_stop", "21:BSB300550000", "BSB300550000")
    monkeypatch.setattr(repository, "nearby_facilities", lambda *args: [station])
    calls, _, _ = setup({"getSttnAcctoArvlPrearngeInfoList": fixture})
    with TestClient(app) as client:
        body = client.get(_url("transit", "fst_000003"), params={"mode": "bus"}).json()
        assert body["status"] == expected
        assert body["stations"][0]["arrivals"] == []
    assert len(calls) == 1


@pytest.mark.parametrize("matched", [True, False])
def test_seoul_bus_crowding_requires_match_and_ignores_item_count(setup, monkeypatch, matched):
    monkeypatch.setenv("TRANSIT_PROVIDER", "real")
    station = _station("bus", "연신내역.로데오거리", 37.5758, 126.9768, "SEOUL", "seoul_bus_stop", "12203", "111000115")
    monkeypatch.setattr(repository, "nearby_facilities", lambda *args: [station])

    def bus_route(request):
        response = _load("seoul_bus_route")
        assert response["msgHeader"]["itemCount"] == 0
        if not matched:
            response["msgBody"]["itemList"][0]["arsId"] = "12345"
        return httpx2.Response(200, json=response)

    calls, _, _ = setup({"getStationByUid": "seoul_bus_station_synthetic", "getArrInfoByRouteAll": bus_route})
    with TestClient(app) as client:
        body = client.get(_url("transit"), params={"mode": "bus"}).json()
        assert body["status"] == "ok"
        (arrival,) = body["stations"][0]["arrivals"]
        assert arrival["eta_s"] == 162
        assert arrival["crowding"] == ("여유" if matched else "unverified")
    assert calls[0][1]["arsId"] == "12203"


def test_stop_fallback_requires_distance_name_line_direction_and_a_single_candidate():
    criteria = dict(ars_id="01234", node_id="100000001", name="서울역", lat=37.55, lng=126.97, line="701", direction="상행")
    candidate = {"stNm": "서울역", "rtNm": "701", "dir": "상행", "gpsY": 37.55026, "gpsX": 126.97}
    assert transit_arrivals.match_seoul_stop([candidate], **criteria) == candidate
    for changes in ({"gpsY": 37.55028}, {"stNm": "시청역"}, {"rtNm": "702"}, {"dir": "하행"}, {"arsId": "04321"}):
        assert transit_arrivals.match_seoul_stop([{**candidate, **changes}], **criteria) is None
    assert transit_arrivals.match_seoul_stop([candidate, dict(candidate)], **criteria) is None


@pytest.mark.parametrize("with_match", [True, False])
def test_tour_forecast_strict_attraction_and_monthly_demand(setup, monkeypatch, tmp_path, with_match):
    monkeypatch.setenv("VISIT_FORECAST_PROVIDER", "real")
    config = tmp_path / "attractions.json"
    config.write_text(json.dumps({
        "fst_000004": {
            "area_code": "26", "district_code": "26350", "attraction": "SEA LIFE 부산아쿠아리움", "approved": True,
        }
    }))
    original = real_festival_info.find_festival

    def festival(festival_id):
        result = original(festival_id)
        if festival_id == "fst_000004":
            return result.model_copy(update={"venue_name": "SEA LIFE 부산아쿠아리움"})
        return result

    monkeypatch.setattr(real_festival_info, "find_festival", festival)
    calls, _, _ = setup({
        "tatsCnctrRatedList": "tour_forecast" if with_match else "tour_no_match_synthetic",
        "areaTarSjrnDsList": "tour_demand",
    })
    monkeypatch.setenv("VISIT_FORECAST_MAPPING_FILE", str(config))
    with TestClient(app) as client:
        assert client.get(_url("visit-forecast")).json()["forecast"]["status"] == "unsupported"
        assert calls == []
        response = client.get(_url("visit-forecast", "fst_000004"), params={"days": 1})
        assert "X-Mock" not in response.headers
        body = response.json()
        assert body["status"] == ("ok" if with_match else "unsupported")
        assert body["region_demand"] == {
            "indicator": "타권역 방문자 비중", "value": 73.39, "base_month": "2026-10", "area_name": "해운대구",
        }
        if with_match:
            assert body["forecast"]["days"] == [{"date": "2026-11-19", "rate": 55.19}]
            assert body["forecast"]["attraction"] == "SEA LIFE 부산아쿠아리움"
        else:
            assert body["forecast"]["days"] == []
        client.get(_url("visit-forecast", "fst_000004"), params={"days": 7})
        assert len(calls) == 2
    demand_query = dict(calls)["areaTarSjrnDsList"]
    assert [demand_query[key] for key in ("areaCd", "signguCd", "tarSjrnDsIxCd", "baseYm")] == [
        "26", "26350", "2101", "202610",
    ]


def test_forecast_daily_snapshots_reused_after_service_restart(setup, monkeypatch, tmp_path):
    monkeypatch.setenv("VISIT_FORECAST_PROVIDER", "real")
    file = tmp_path / "attractions.json"
    file.write_text(json.dumps({
        "fst_000004": {
            "area_code": "26", "district_code": "26350", "attraction": "해운대해수욕장", "approved": True,
        }
    }))
    snapshots = {}

    def save(source, target, region, reading):
        assert region == "BUSAN"
        snapshots[(source, target)] = reading

    def read(source, target, since, now):
        reading = snapshots.get((source, target))
        if reading is not None and since <= reading.observed_at <= now:
            return reading
        return None

    def page(request):
        body = _load("tour_forecast")
        data = body["response"]["body"]
        index = int(request.url.params["pageNo"]) - 1
        data["items"]["item"] = [{**data["items"]["item"][index], "tAtsNm": "해운대해수욕장"}]
        return httpx2.Response(200, json=body)

    monkeypatch.setattr(repository, "save_tour_snapshot", save)
    monkeypatch.setattr(repository, "read_tour_snapshot", read)
    calls, _, _ = setup({"tatsCnctrRatedList": page, "areaTarSjrnDsList": "tour_empty"})
    monkeypatch.setenv("VISIT_FORECAST_MAPPING_FILE", str(file))
    monkeypatch.setenv("VISIT_FORECAST_STORE", "db")
    with TestClient(app) as client:
        body = client.get(_url("visit-forecast", "fst_000004")).json()
        assert body["forecast"]["status"] == "ok" and len(body["forecast"]["days"]) == 3
        assert body["region_demand"] is None
    assert len(calls) == 4
    assert {source for source, _ in snapshots} == {"visit_forecast", "region_demand"}

    setup({})
    monkeypatch.setenv("VISIT_FORECAST_MAPPING_FILE", str(file))
    monkeypatch.setenv("VISIT_FORECAST_STORE", "db")
    with TestClient(app) as client:
        assert client.get(_url("visit-forecast", "fst_000004")).json() == body


def test_notice_queries_real_repository_filters_and_nullable_fields(setup, monkeypatch):
    monkeypatch.setenv("NOTICES_PROVIDER", "real")
    setup({})
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    monkeypatch.setattr(repository, "get_festival_engine", lambda: engine)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE TABLE official_notices (
                notice_id TEXT, festival_id TEXT, type TEXT, title TEXT, content TEXT,
                effective_from TEXT, effective_to TEXT, source_id TEXT, source_url TEXT,
                published_at TEXT, control_version TEXT, approval_status TEXT
            )
        """))
        connection.execute(text("""
            INSERT INTO official_notices VALUES
                ('open','fst_000001','operation','열린 공지',NULL,NULL,NULL,'admin_manual',NULL,NULL,NULL,'approved'),
                ('pending','fst_000001','operation','대기',NULL,NULL,NULL,'admin_manual',NULL,NULL,NULL,'pending'),
                ('rejected','fst_000001','operation','거절',NULL,NULL,NULL,'admin_manual',NULL,NULL,NULL,'rejected'),
                ('past','fst_000001','road_closure','종료',NULL,NULL,'2026-11-18T00:00:00+09:00','seoul_topis',NULL,NULL,'v1','approved'),
                ('future','fst_000001','road_closure','예정',NULL,'2026-11-20T00:00:00+09:00',NULL,'seoul_topis',NULL,NULL,'v2','approved'),
                ('different','fst_000002','operation','타 축제',NULL,NULL,NULL,'admin_manual',NULL,NULL,NULL,'approved')
        """))
    with TestClient(app) as client:
        response = client.get(_url("notices"))
        assert "X-Mock" not in response.headers
        (notice,) = response.json()["items"]
        assert notice["notice_id"] == "open"
        assert notice["source"] == "admin_manual" and notice["content"] is None
        categories = {"type": "road_closure", "active_only": "false"}
        assert [item["notice_id"] for item in client.get(_url("notices"), params=categories).json()["items"]] == [
            "future", "past",
        ]
        empty = client.get(_url("notices", "fst_000006")).json()
        assert empty["status"] == "ok" and empty["items"] == []
    engine.dispose()


def test_tour_forecast_uses_explicit_approval_and_confirmed_venue(monkeypatch, tmp_path):
    festival_id = "fst_01M835B57450M888RBNEFVRWWA"
    venue = "청계천(청계광장 ~ 삼일교)"
    monkeypatch.delenv("VISIT_FORECAST_MAPPING_FILE", raising=False)
    assert visit_forecast.find_attraction(festival_id, venue) is None

    candidate = {"area_code": "11", "district_code": "11110", "attraction": venue}
    for approval in ({}, {"approved": False}, {"approved": True}):
        config = tmp_path / f"attraction-{approval.get('approved')}.json"
        config.write_text(json.dumps({festival_id: candidate | approval}), encoding="utf-8")
        monkeypatch.setenv("VISIT_FORECAST_MAPPING_FILE", str(config))
        assert (visit_forecast.find_attraction(festival_id, venue) is not None) == (approval.get("approved") is True)
        assert visit_forecast.find_attraction(festival_id, "청계광장") is None


def test_new_endpoints_default_to_mock(setup, monkeypatch):
    for env in ("TRANSIT_PROVIDER", "VISIT_FORECAST_PROVIDER"):
        monkeypatch.delenv(env, raising=False)
    setup({})
    with TestClient(app) as client:
        for endpoint in ("transit", "visit-forecast"):
            response = client.get(_url(endpoint))
            assert response.headers["X-Mock"] == "true"
            assert response.json()["is_mock"] is True
            assert response.json()["status"] == "ok"
