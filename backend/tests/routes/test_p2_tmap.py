import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any

import httpx2
import pytest

from api.providers.route_base import ErrorKind, ProviderError, RouteQuery
from api.providers.tmap import TmapClient
from . import FIXTURES, QUERY, TEST_KEY


@pytest.fixture(autouse=True)
def set_test_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TMAP_APP_KEY", TEST_KEY)


def test_P2_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TMAP_APP_KEY")
    with pytest.raises(ProviderError) as caught:
        TmapClient()
    assert caught.value.kind == "config"
    assert caught.value.provider == "tmap"


@pytest.mark.parametrize(
    ("depart_at", "search_dttm"),
    [(None, None), (datetime(2026, 11, 19, 8, 30, tzinfo=timezone.utc), "202611191730")],
)
def test_P2_request_config_and_key_hidden(
    caplog: pytest.LogCaptureFixture, depart_at: datetime | None, search_dttm: str | None
) -> None:
    caplog.set_level(logging.DEBUG)
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        assert request.method == "POST"
        assert str(request.url) == "https://apis.openapi.sk.com/transit/routes"
        assert request.headers["appKey"] == TEST_KEY
        assert request.headers["Accept"] == request.headers["Content-Type"] == "application/json"
        assert request.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 5.0)
        expected = {
            "startX": QUERY.origin[1], "startY": QUERY.origin[0],
            "endX": QUERY.destination[1], "endY": QUERY.destination[0],
            "count": 3, "lang": 0, "format": "json",
        }
        if search_dttm is not None:
            expected["searchDttm"] = search_dttm
        assert json.loads(request.content) == expected
        logging.getLogger("httpcore2.http11").debug("요청 헤더 %s", request.headers["appKey"])
        return httpx2.Response(403, json={"error": {"message": TEST_KEY}})

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        client = TmapClient(http)
        with pytest.raises(ProviderError) as caught:
            client.query(RouteQuery(QUERY.origin, QUERY.destination, depart_at))
    assert calls == 1
    assert caught.value.kind == "config"
    assert TEST_KEY not in str(caught.value)
    assert TEST_KEY not in repr(caught.value)
    assert TEST_KEY not in caught.value.detail
    assert TEST_KEY not in repr(client)
    assert TEST_KEY not in caplog.text


@pytest.mark.parametrize(
    ("status", "payload", "kind"),
    [
        (403, json.loads((FIXTURES / "tmap_error_key.json").read_text()), "config"),
        (401, {"result": {"status": 23}}, "config"),
        (403, {}, "config"),
        (200, {"result": {"status": 11}}, "too_close"),
        (200, {"result": {"status": 12}}, "no_result"),
        (200, {"result": {"status": 13}}, "no_result"),
        (200, {"result": {"status": 14}}, "no_result"),
        (400, {"result": {"status": 21}}, "bad_request"),
        (400, {"result": {"status": 22}}, "bad_request"),
        (400, {"result": {"status": 24}}, "bad_request"),
        (400, {"result": {"status": "23"}}, "region"),
        (429, {"result": {"status": 23}}, "quota"),
        (500, {"result": {"status": 31}}, "temporary"),
        (502, {"result": {"status": 32}}, "temporary"),
        (503, {"result": {"status": 31}}, "temporary"),
        (504, {"result": {"status": 11}}, "temporary"),
        (200, {"metaData": {"plan": {}}}, "no_result"),
        (200, {"metaData": {"plan": {"itineraries": []}}}, "no_result"),
        (200, None, "temporary"),
    ],
)
def test_P3_http_then_body_error(
    status: int, payload: dict[str, Any] | None, kind: ErrorKind
) -> None:
    def handler(_: httpx2.Request) -> httpx2.Response:
        if payload is None:
            return httpx2.Response(status, text=TEST_KEY)
        return httpx2.Response(status, json=payload)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        with pytest.raises(ProviderError) as caught:
            TmapClient(http).query(QUERY)
    assert caught.value.kind == kind
    assert TEST_KEY not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(
    ("error", "kind"), [(httpx2.ReadTimeout, "timeout"), (httpx2.ConnectError, "temporary")]
)
def test_P3_transport_error_without_retry_or_leaked_context(
    error: type[httpx2.RequestError], kind: ErrorKind
) -> None:
    calls = 0

    def handler(request: httpx2.Request) -> httpx2.Response:
        nonlocal calls
        calls += 1
        raise error(TEST_KEY, request=request)

    with httpx2.Client(transport=httpx2.MockTransport(handler)) as http:
        with pytest.raises(ProviderError) as caught:
            TmapClient(http).query(QUERY)
    assert caught.value.kind == kind
    assert calls == 1
    assert caught.value.__context__ is None
    assert TEST_KEY not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize(("city", "mode", "fare"), [("seoul", "bus", 1500), ("busan", "subway", 1600)])
def test_P4_normalizes_synthetic_itinerary(city: str, mode: str, fare: int) -> None:
    body = json.loads((FIXTURES / f"tmap_{city}.json").read_text())
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        result = TmapClient(http).query(QUERY)
    candidate, = result.candidates
    assert candidate["candidate_id"] == "c1"
    assert candidate["summary"] == ("버스 1회" if mode == "bus" else "지하철 1회")
    assert candidate["duration_min"] == 18
    assert candidate["fare_krw"] == fare
    assert candidate["service_running"] is True
    assert result.notices == []
    itinerary = body["metaData"]["plan"]["itineraries"][0]
    assert candidate["walk_m"] == itinerary["totalWalkDistance"]
    assert candidate["distance_m"] == itinerary["totalDistance"]
    assert candidate["transfers"] == itinerary["transferCount"]
    assert candidate["mode_evidence"] == {
        "bus_crowding": {"status": "unverified", "reason": "버스 혼잡을 확인하지 않았어요."}
    }
    legs = candidate["legs"]
    assert [leg["mode"] for leg in legs] == ["walk", mode, "walk"]
    for leg in legs:
        assert leg["path"]
        assert all(33 <= lat <= 39 and 124 <= lng <= 132 for lat, lng in leg["path"])
    if city == "seoul":
        assert legs[0]["path"][:2] == [[37.5668, 126.99051], [37.566244, 126.99047]]
        assert legs[1]["duration_min"] == 6
        assert legs[1]["line"] == "예시노선-0001"
        assert legs[1]["stops"][0] == {
            "name": "예시정류장-0001", "id": "S0001", "lat": 37.564547, "lng": 126.990717
        }


@pytest.mark.parametrize(
    ("services", "running"),
    [
        ([(0, [0, 1])], True),
        ([(0, [0, 0])], False),
        ([(1, []), (0, [0])], False),
        ([(1, []), (0, [1])], True),
        ([(None, []), (0, [0])], False),
        ([(None, [])], None),
        ([(0, [None])], None),
    ],
)
def test_P13_all_transit_legs_are_checked(
    services: list[tuple[int | None, list[int | None]]], running: bool | None
) -> None:
    legs = [
        {
            "mode": "SUBWAY", "sectionTime": 61, "service": service,
            "Lane": [{"service": alternative} for alternative in alternatives],
            "passShape": {"linestring": "126.12345678,37.12345678"},
        }
        for service, alternatives in services
    ]
    itinerary = {
        "totalTime": 181, "totalDistance": 1234, "totalWalkDistance": 12,
        "transferCount": len(legs) - 1, "fare": {"regular": {"totalFare": 1500}}, "legs": legs,
    }
    body = {"metaData": {"plan": {"itineraries": [itinerary] * 4}}}
    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        client = TmapClient(http)
        if running is False:
            with pytest.raises(ProviderError) as caught:
                client.query(QUERY)
            assert caught.value.kind == "service_ended"
            return
        result = client.query(QUERY)

    assert [candidate["candidate_id"] for candidate in result.candidates] == ["c1", "c2", "c3"]
    assert result.candidates[0]["service_running"] is running
    assert result.candidates[0]["legs"][0]["path"] == [[37.123457, 126.123457]]
    if len(legs) == 2:
        assert result.candidates[0]["summary"] == "지하철 1회 환승"
    assert result.notices == []


@pytest.mark.parametrize("primary_service", [0, None], ids=["ended", "missing"])
def test_P13_unnamed_running_alternative_omits_line(primary_service: int | None) -> None:
    body = json.loads((FIXTURES / "tmap_seoul.json").read_text())
    leg = body["metaData"]["plan"]["itineraries"][0]["legs"][1]
    leg["route"] = "합성예시 대표 노선"
    leg["Lane"] = [{"service": 1}]
    if primary_service is None:
        del leg["service"]
    else:
        leg["service"] = primary_service

    with httpx2.Client(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, json=body))) as http:
        result = TmapClient(http).query(QUERY)

    candidate, = result.candidates
    assert candidate["service_running"] is True
    assert "line" not in candidate["legs"][1]
