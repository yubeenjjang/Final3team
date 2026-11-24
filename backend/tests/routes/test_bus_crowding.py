import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.providers import bus_crowding as seoul_bus
from api.providers.festival_source import FestivalSource
from api.providers.transit_arrivals import seoul_bus_crowding
from api.services import bus_crowding
from tests.routes.test_p9_real_routes import FakeProvider, routes  # noqa: F401

_FIXTURES = Path(__file__).resolve().parents[3] / "Docs" / "Step 2" / "evidence" / "responses"
RETURN = "/api/v1/routes/return"
TOKEN = "X-Route-Access-Token"
BODY = {"request_id": "test-bus-crowding", "festival_id": "fst_000001", "destination": {"lat": 37.58, "lng": 126.92}}
_KEY = "synthetic-key-for-log-test"
_LAT, _LNG = 37.59, 126.91
_AREA = {"crowd_areas": [], "traffic_incidents": []}
_UPSTREAM = "seoul_bus_15000314"


def _fixture(suffix):
    return json.loads((_FIXTURES / f"2026-11-19_seoul-bus_{suffix}.json").read_text())


def _items(rows):
    return {"msgHeader": {"headerCd": "0", "itemCount": 0}, "msgBody": {"itemList": rows}}


@dataclass
class BusRouteProvider(FakeProvider):
    following: str = "신흥시장"
    line: str = "간선:７５３번"
    lat: float = _LAT

    def query(self, query):
        result = super().query(query)
        candidate = result.candidates[0]
        candidate["legs"] = [
            {"mode": "walk"},
            {"mode": "bus", "line": self.line, "stops": [
                {"id": "121670", "name": "응암역 · 신사오거리 ", "lat": self.lat, "lng": _LNG},
                {"id": "765432", "name": self.following},
            ]},
        ]
        result.candidates.append(deepcopy(candidate))
        result.candidates[1]["candidate_id"] = "c2"
        # 선택하지 않은 후보의 외부 조회가 있었는지 구별할 수 있게 만든다.
        result.candidates[1]["legs"][1]["stops"][0]["lat"] = self.lat + 0.003
        return result


@pytest.fixture
def source(monkeypatch, tmp_path):
    monkeypatch.setenv("BUS_CROWD_PROVIDER", "real")
    monkeypatch.setenv("DATA_GO_KR_SERVICE_KEY", _KEY)
    monkeypatch.setenv("FESTIVAL_INFO_QUOTA_FILE", str(tmp_path / "quota.json"))
    calls = []
    clock = [0.0]
    position = {
        "arsId": "12167", "stationId": "111000079", "stationNm": "응암역.신사오거리",
        "gpsY": str(_LAT), "gpsX": str(_LNG),
    }

    def setup(case, *, delay=0):
        route = _fixture("100100118")
        route_rows = route["msgBody"]["itemList"]
        stations = [position]
        if case == "distance":
            position["gpsY"] = str(_LAT + 0.00031)  # 약 34m
        if case == "duplicate":
            stations.append({**position, "arsId": "12178", "stationId": "111000090"})
            route_rows.extend([
                {**route_rows[14], "arsId": "12178", "stId": "111000090", "staOrd": "201"},
                {**route_rows[15], "staOrd": "202"},
            ])

        async def respond(request):
            name = request.url.path.rsplit("/", 1)[1]
            params = request.url.params
            calls.append(name)
            assert params["serviceKey"] == _KEY
            if delay:
                await asyncio.sleep(delay)
            if name == "getStationByPos":
                assert float(params["tmY"]) == _LAT and int(params["radius"]) == 30
                return httpx2.Response(200, json=_items(stations))
            if name == "getStationByUid":
                return httpx2.Response(200, json=_items([
                    {"arsId": params["arsId"], "rtNm": "753", "busRouteId": "100100118"}
                ]))
            assert name == "getArrInfoByRouteAll" and params["busRouteId"] == "100100118"
            if case == "key_error":
                return httpx2.Response(403, json=_fixture("오류-키오류"))
            return httpx2.Response(200, json=route)

        client = FestivalSource(transport=httpx2.MockTransport(respond), clock=lambda: clock[0])
        monkeypatch.setattr(bus_crowding, "get_client", lambda: client)
        return calls, clock

    return setup


def evidence(body, index=0):
    return body["route_candidates"][index]["mode_evidence"]["bus_crowding"]


def test_only_valid_crowding_code_is_returned_per_arrival():
    reading = {"rerdie_Div1": "4", "reride_Num1": "5", "rerdie_Div2": "0", "reride_Num2": "4"}
    assert seoul_bus_crowding(reading, 1) == "혼잡"
    assert seoul_bus_crowding(reading, 2) is None
    assert seoul_bus_crowding({**reading, "reride_Num1": "0"}, 1) is None


@pytest.mark.parametrize(("case", "expected_calls"), [
    ("direction", 3), ("distance", 1), ("duplicate", 4), ("line", 2), ("key_error", 3),
])
def test_selection_with_no_unique_crowding_keeps_route(routes, monkeypatch, source, caplog, case, expected_calls):
    calls, _ = source(case)
    tmap = BusRouteProvider(
        "tmap", routes.clock,
        following="역촌초등학교" if case == "direction" else "신흥시장",
        line="999" if case == "line" else "753",
    )
    monkeypatch.setattr(routes.tmap, "query", tmap.query)
    with caplog.at_level(logging.DEBUG):
        ready = routes.client.post(RETURN, json=BODY)
        assert ready.status_code == 200 and calls == []
        response = routes.client.get(
            f"{RETURN}/{ready.json()['route_request_id']}",
            headers={TOKEN: ready.headers[TOKEN]}, params={"candidate_id": "c1"},
        )
    body = response.json()
    assert response.status_code == 200 and body["route_status"] == "ready"
    assert evidence(body)["status"] == "unknown"
    assert len(calls) == expected_calls
    assert _KEY not in caplog.text and "serviceKey=" not in caplog.text
    assert "정상적으로 처리되었습니다." not in caplog.text


def test_sync_selection_enriches_only_selected_candidate_and_caches_60_seconds(routes, monkeypatch, source):
    calls, clock = source("success", delay=0.01)
    monkeypatch.setattr(routes.tmap, "query", BusRouteProvider("tmap", routes.clock).query)
    ready = routes.client.post(RETURN, json=BODY, headers={"Origin": "http://localhost:5173"})
    assert ready.status_code == 200 and calls == []
    assert TOKEN in ready.headers["Access-Control-Expose-Headers"]
    assert "no-store" in ready.headers["Cache-Control"]
    route_id = ready.json()["route_request_id"]
    url = f"{RETURN}/{route_id}"
    params = {"candidate_id": "c1"}
    headers = {TOKEN: ready.headers[TOKEN]}
    assert routes.client.get(url, params=params).status_code == 401
    assert routes.client.get(url, headers={TOKEN: "wrong-token"}, params=params).status_code == 403
    assert routes.client.get(url, headers=headers, params={"candidate_id": "c9"}).status_code == 404
    assert routes.client.get(url, headers=headers, params={"candidate_id": "invalid"}).status_code == 422
    assert routes.client.get(url, headers=headers).json()["route_candidates"] == ready.json()["route_candidates"]
    assert calls == []

    with ThreadPoolExecutor(max_workers=2) as pool:
        selections = [pool.submit(routes.client.get, url, headers=headers, params=params) for _ in range(2)]
        selected, concurrent = [selection.result() for selection in selections]
    assert concurrent.json() == selected.json()
    assert selected.status_code == 200 and "no-store" in selected.headers["Cache-Control"]
    body = selected.json()
    assert evidence(body) == {
        "status": "available", "source": _UPSTREAM, "is_mock": False,
        "legs": [{"leg_index": 1, "status": "available", "arrivals": [
            {"arrival_order": 1, "crowding": "보통"}, {"arrival_order": 2, "crowding": "여유"},
        ]}],
    }
    assert body["route_candidates"][1] == ready.json()["route_candidates"][1]
    assert all(candidate["area_evidence"] == _AREA for candidate in body["route_candidates"])
    assert routes.client.get(url, headers=headers).json()["route_candidates"] == ready.json()["route_candidates"]
    clock[0] = 59.9
    assert evidence(routes.client.get(url, headers=headers, params=params).json()) == evidence(body)
    assert len(calls) == 3
    clock[0] = 60
    assert evidence(routes.client.get(url, headers=headers, params=params).json()) == evidence(body)
    assert len(calls) == 6


def test_timeout_preserves_route_and_next_read_can_recover(routes, monkeypatch, source):
    calls, _ = source("success", delay=0.05)
    monkeypatch.setattr(seoul_bus, "LOOKUP_TIMEOUT_S", 0.02)
    monkeypatch.setattr(routes.tmap, "query", BusRouteProvider("tmap", routes.clock).query)
    ready = routes.client.post(RETURN, json=BODY)
    url = f"{RETURN}/{ready.json()['route_request_id']}"
    headers = {TOKEN: ready.headers[TOKEN]}
    params = {"candidate_id": "c1"}
    failed = routes.client.get(url, headers=headers, params=params).json()
    assert failed["completed_valid_route"] and evidence(failed)["status"] == "unknown"
    assert calls == ["getStationByPos"]
    monkeypatch.setattr(seoul_bus, "LOOKUP_TIMEOUT_S", 1)
    assert evidence(routes.client.get(url, headers=headers, params=params).json())["status"] == "available"


@pytest.mark.parametrize("scenario", ["sync_bus_ready", "async_bus_ready"])
def test_default_mock_for_sync_and_async_routes(monkeypatch, scenario):
    monkeypatch.setenv("ROUTE_PROVIDER", "mock")
    monkeypatch.delenv("BUS_CROWD_PROVIDER", raising=False)
    def unexpected():
        pytest.fail("모의 혼잡은 외부 공급원을 사용하지 않아야 합니다.")
    monkeypatch.setattr(bus_crowding, "get_client", unexpected)
    with TestClient(app) as client:
        submitted = client.post(RETURN, json={**BODY, "request_id": scenario}, headers={"X-Mock-Scenario": scenario})
        body = submitted.json()
        url = f"{RETURN}/{body['route_request_id']}"
        if scenario == "async_bus_ready":
            assert submitted.status_code == 202
            headers = {TOKEN: body["route_access_token"]}
            assert client.get(url, headers=headers, params={"candidate_id": "c1"}).json()["route_status"] == "processing"
            body = client.get(url, headers=headers).json()
        else:
            assert submitted.status_code == 200
            headers = {TOKEN: submitted.headers[TOKEN]}
        assert evidence(body)["status"] == "unverified"
        selected = client.get(url, headers=headers, params={"candidate_id": "c1"}).json()
        assert evidence(selected)["status"] == "available"
        assert evidence(selected)["is_mock"] is True


def test_kakao_is_unsupported_even_in_real_mode(monkeypatch):
    monkeypatch.setenv("ROUTE_PROVIDER", "mock")
    monkeypatch.setenv("BUS_CROWD_PROVIDER", "real")
    with TestClient(app) as client:
        submitted = client.post(
            RETURN, json={**BODY, "request_id": "test-kakao"}, headers={"X-Mock-Scenario": "sync_secondary"},
        )
    assert submitted.status_code == 200 and TOKEN not in submitted.headers
    assert submitted.json()["provider"] == "kakao"
    assert evidence(submitted.json())["status"] == "unsupported"


def test_out_of_seoul_does_not_contact_supplier(routes, monkeypatch):
    monkeypatch.setenv("BUS_CROWD_PROVIDER", "real")
    monkeypatch.setattr(routes.tmap, "query", BusRouteProvider("tmap", routes.clock, lat=35.1).query)
    def unexpected():
        pytest.fail("서울 밖의 정류장을 외부에서 조회했습니다.")
    monkeypatch.setattr(bus_crowding, "get_client", unexpected)
    ready = routes.client.post(RETURN, json=BODY)
    selected = routes.client.get(
        f"{RETURN}/{ready.json()['route_request_id']}", headers={TOKEN: ready.headers[TOKEN]},
        params={"candidate_id": "c1"},
    ).json()
    assert evidence(selected)["status"] == "unsupported"
