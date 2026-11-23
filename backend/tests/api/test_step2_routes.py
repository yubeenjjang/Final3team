import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from api.mocks.store import reset_store, route_requests
from api.services.mock_routes import create_ready_route

_RETURN = "/api/v1/routes/return"
_VISIT = "/api/v1/routes/visit"
_TOKEN_HEADER = "X-Route-Access-Token"
_SCENARIO_HEADER = "X-Mock-Scenario"
_COMMON_FIELDS = {"request_id": "step2-request-01", "festival_id": "fst_000001"}
_RETURN_BODY = {**_COMMON_FIELDS, "destination": {"query": "서울역"}}
_VISIT_BODY = {**_COMMON_FIELDS, "origin": {"query": "서울역"}}


def _success(response: Response, status: int) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    return body


def _error(response: Response, status: int, code: str, *, retryable: bool = False) -> str:
    assert response.status_code == status
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert set(error) == {"code", "message", "request_id", "retryable"}
    assert error["code"] == code
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert error["retryable"] is retryable
    assert re.search("[가-힣]", error["message"])
    return error["message"]


def _poll(client: TestClient, queued: dict[str, Any]) -> dict[str, Any]:
    return _success(
        client.get(queued["status_url"], headers={_TOKEN_HEADER: queued["route_access_token"]}),
        200,
    )


@pytest.mark.parametrize(
    ("url", "body", "field"),
    [
        (_RETURN, _COMMON_FIELDS, "destination"),
        (_RETURN, {**_RETURN_BODY, "destination": {"query": "서울역", "lat": 37.5, "lng": 126.9}}, "destination"),
        (
            _RETURN,
            {
                **_COMMON_FIELDS,
                "origin": {"type": "festival"},
                "destination": {"type": "festival"},
            },
            "destination",
        ),
        (_RETURN, {**_RETURN_BODY, "travel_mode": "bike"}, "travel_mode"),
        (_RETURN, {**_RETURN_BODY, "destination": {}}, "destination"),
        (_RETURN, {**_RETURN_BODY, "destination": {"lat": 37.5}}, "destination"),
        (_RETURN, {**_RETURN_BODY, "destination": {"lat": 40, "lng": 126.9}}, "lat"),
        (_RETURN, {**_RETURN_BODY, "user_constraints": {"max_walk_m": 5001}}, "max_walk_m"),
        (_VISIT, _COMMON_FIELDS, "origin"),
        (_VISIT, {**_VISIT_BODY, "origin": {"type": "festival"}}, "destination"),
    ],
)
def test_R10_invalid_route_inputs(
    client: TestClient, url: str, body: dict[str, object], field: str
) -> None:
    message = _error(client.post(url, json=body), 422, "VALIDATION_ERROR")
    assert field in message


def test_R11_default_route_is_queued(client: TestClient) -> None:
    queued = _success(client.post(_RETURN, json=_RETURN_BODY), 202)
    assert set(queued) == {
        "route_request_id", "route_status", "status_url", "route_access_token",
        "retry_after_s", "is_mock",
    }
    assert re.fullmatch(r"rr_[0-9A-Za-z]{16}", queued["route_request_id"])
    assert re.fullmatch(r"rrt_[0-9A-Za-z]{24}", queued["route_access_token"])
    assert queued["status_url"] == f"{_RETURN}/{queued['route_request_id']}"
    assert queued["route_status"] == "queued"
    assert queued["retry_after_s"] == 2


def test_R11_sync_ready_payload_and_lookup(client: TestClient) -> None:
    ready = _success(
        client.post(
            _RETURN,
            headers={_SCENARIO_HEADER: "sync_ready"},
            json={
                **_RETURN_BODY,
                "destination": {"type": "place", "lat": 37.5, "lng": 126.9},
                "travel_mode": "taxi",
                "route_preference": "accessible",
                "user_constraints": {"with_child": True, "wheelchair": True, "max_walk_m": 0},
            },
        ),
        200,
    )
    route_id, token = ready["route_request_id"], ready["route_access_token"]
    queried_at = ready["queried_at"]
    candidates = ready.pop("route_candidates")
    assert datetime.fromisoformat(queried_at).utcoffset() == timedelta(hours=9)
    assert re.fullmatch(r"rrt_[0-9A-Za-z]{24}", token)
    assert ready == {
        "route_request_id": route_id,
        "route_access_token": token,
        "route_status": "ready",
        "direction": "return",
        "festival_id": "fst_000001",
        "origin": {"type": "festival", "name": "광화문광장", "lat": 37.5759, "lng": 126.9768},
        "destination": {"type": "place", "label": "37.5,126.9"},
        "travel_mode": "taxi",
        "route_preference": "accessible",
        "provider": "mock_adapter",
        "provider_tier": "mock",
        "queried_at": queried_at,
        "verification_status": "control_unverified",
        "completed_valid_route": True,
        "constraint_status": {
            "with_child": "not_verifiable",
            "wheelchair": "not_verifiable",
            "max_walk_m": "not_verifiable",
            "control": "unverified",
        },
        "coverage": {"scope": "national", "region_code": "SEOUL", "supported": True},
        "score_version": None,
        "notices": ["공식 교통통제 반영 여부를 확인하지 못했어요."],
        "is_mock": True,
    }
    candidate, = candidates
    legs = candidate["legs"]
    assert candidate == {
        "candidate_id": "c1",
        "summary": "지하철 1회 환승(모의)",
        "duration_min": 38,
        "distance_m": 9200,
        "walk_m": 650,
        "transfers": 1,
        "fare_krw": 1550,
        "legs": legs,
        "service_running": True,
        "score": None,
        "area_evidence": {"crowd_areas": [], "traffic_incidents": []},
        "mode_evidence": {"bus_crowding": {"status": "unverified", "reason": "모의 응답"}},
    }
    assert [{key: value for key, value in leg.items() if key != "path"} for leg in legs] == [
        {"mode": "walk", "duration_min": 6},
        {"mode": "subway", "line": "(모의)", "duration_min": 24},
        {"mode": "walk", "duration_min": 8},
    ]
    for leg in legs:
        assert len(leg["path"]) == 2
        for lat, lng in leg["path"]:
            assert 33 <= lat <= 39
            assert 124 <= lng <= 132
    assert legs[0]["path"][0] == [37.5759, 126.9768]
    assert legs[-1]["path"][-1] == [37.5, 126.9]
    lookup = _success(client.get(f"{_RETURN}/{route_id}", headers={_TOKEN_HEADER: token}), 200)
    assert lookup == {**ready, "route_candidates": candidates, "updated_at": queried_at}


def test_R11_route_validation_precedes_scenario(client: TestClient) -> None:
    headers = {_SCENARIO_HEADER: "unknown"}
    invalid = {**_RETURN_BODY, "destination": {"query": "가는 길에 없는곳"}}
    for festival_id, status, code in (
        ("fst_999999", 404, "FESTIVAL_NOT_FOUND"),
        ("fst_000006", 400, "FESTIVAL_LOCATION_UNKNOWN"),
        ("fst_000001", 400, "ROUTE_INVALID"),
    ):
        response = client.post(_RETURN, json={**invalid, "festival_id": festival_id}, headers=headers)
        message = _error(response, status, code)
        if code == "ROUTE_INVALID":
            assert message == "목적지를 찾을 수 없어요"


def test_R11_unknown_festival_location_allows_two_user_places(client: TestClient) -> None:
    body = {
        **_RETURN_BODY,
        "festival_id": "fst_000006",
        "origin": {"type": "place", "query": "광화문"},
    }
    _success(client.post(_RETURN, json=body), 202)


def test_R11_idempotency_replays_original_and_rejects_changes(client: TestClient) -> None:
    original = _success(client.post(_RETURN, json=_RETURN_BODY), 202)
    assert _success(client.post(_RETURN, json=_RETURN_BODY), 202) == original
    _poll(client, original)
    _poll(client, original)
    replay = _success(
        client.post(
            _RETURN,
            json=dict(reversed(list(_RETURN_BODY.items()))),
            headers={_SCENARIO_HEADER: "unknown"},
        ),
        202,
    )
    assert replay == original
    assert len(route_requests) == 1
    _error(
        client.post(
            _RETURN, json={**_RETURN_BODY, "destination": {"query": "홍대입구역"}},
            headers={_SCENARIO_HEADER: "unknown"},
        ),
        409, "IDEMPOTENCY_CONFLICT",
    )


def test_R11_overloaded_request_is_recorded_as_rejected(client: TestClient) -> None:
    _error(
        client.post(_RETURN, json=_RETURN_BODY, headers={_SCENARIO_HEADER: "overloaded"}),
        503, "ROUTE_OVERLOADED", retryable=True,
    )
    record, = route_requests.values()
    assert record.status == "rejected"
    _error(client.post(_RETURN, json=_RETURN_BODY), 503, "ROUTE_OVERLOADED", retryable=True)
    assert len(route_requests) == 1


def test_R11_unknown_scenario_does_not_create_request(client: TestClient) -> None:
    _error(
        client.post(_RETURN, json=_RETURN_BODY, headers={_SCENARIO_HEADER: "unknown"}),
        422, "VALIDATION_ERROR",
    )
    assert not route_requests


def test_R12_default_polling_stays_ready(client: TestClient) -> None:
    queued = _success(client.post(_RETURN, json=_RETURN_BODY), 202)
    processing = _poll(client, queued)
    assert processing == {
        "route_request_id": queued["route_request_id"],
        "route_status": "processing",
        "completed_valid_route": False,
        "retry_after_s": 2,
        "updated_at": processing["updated_at"],
        "is_mock": True,
    }
    ready = _poll(client, queued)
    assert ready["route_status"] == "ready"
    assert ready["completed_valid_route"] is True
    assert ready["destination"] == {"type": "place", "label": "서울역"}
    assert ready["travel_mode"] == "transit"
    assert ready["route_preference"] == "fastest"
    assert ready["constraint_status"] == {"control": "unverified"}
    assert ready["updated_at"] == ready["queried_at"]
    assert datetime.fromisoformat(ready["updated_at"]) >= datetime.fromisoformat(processing["updated_at"])
    assert _poll(client, queued) == ready


def test_R12_lookup_validates_id_and_token_without_advancing_state(client: TestClient) -> None:
    first = _success(client.post(_RETURN, json=_RETURN_BODY), 202)
    second = _success(
        client.post(_RETURN, json={**_RETURN_BODY, "request_id": "step2-request-02"}), 202,
    )
    headers = {_TOKEN_HEADER: second["route_access_token"]}
    _error(client.get(first["status_url"]), 401, "UNAUTHORIZED")
    _error(client.get(first["status_url"], headers=headers), 403, "FORBIDDEN")
    _error(client.get(f"{_RETURN}/rr_zzzzzzzz", headers=headers), 404, "ROUTE_REQUEST_NOT_FOUND")
    _error(client.get(f"{_RETURN}/rr_invalid-id", headers=headers), 422, "VALIDATION_ERROR")
    assert _poll(client, first)["route_status"] == "processing"


@pytest.mark.parametrize(
    ("scenario", "status", "code"),
    [
        ("async_unavailable", "unavailable", "ROUTE_UPSTREAM_ERROR"),
        ("async_timeout", "timed_out", "ROUTE_TIMEOUT"),
    ],
)
def test_R12_async_failure_is_a_successful_lookup(
    client: TestClient, scenario: str, status: str, code: str
) -> None:
    queued = _success(client.post(_RETURN, json=_RETURN_BODY, headers={_SCENARIO_HEADER: scenario}), 202)
    assert _poll(client, queued)["route_status"] == "processing"
    failed = _poll(client, queued)
    assert failed["route_status"] == status
    assert failed["completed_valid_route"] is False
    assert set(failed) == {
        "route_request_id", "route_status", "completed_valid_route", "updated_at",
        "is_mock", "error", "notices",
    }
    error = failed["error"]
    assert set(error) == {"code", "message", "retryable"}
    assert error["code"] == code
    assert error["retryable"] is True
    assert re.search("[가-힣]", error["message"])
    assert failed["notices"]
    assert _poll(client, queued) == failed


def test_R13_visit_defaults_to_festival_destination(client: TestClient) -> None:
    queued = _success(client.post(_VISIT, json=_VISIT_BODY), 202)
    assert queued["status_url"] == f"{_VISIT}/{queued['route_request_id']}"
    assert _poll(client, queued)["route_status"] == "processing"
    ready = _poll(client, queued)
    assert ready["route_status"] == "ready"
    assert ready["completed_valid_route"] is True
    assert ready["direction"] == "visit"
    assert ready["origin"] == {"type": "place", "label": "서울역"}
    assert ready["destination"]["type"] == "festival"


def test_R13_route_ids_are_only_available_in_their_direction(client: TestClient) -> None:
    for submit_url, body, other_url in (
        (_RETURN, _RETURN_BODY, _VISIT),
        (_VISIT, _VISIT_BODY, _RETURN),
    ):
        queued = _success(client.post(submit_url, json=body), 202)
        response = client.get(
            f"{other_url}/{queued['route_request_id']}",
            headers={_TOKEN_HEADER: queued["route_access_token"]},
        )
        _error(response, 404, "ROUTE_REQUEST_NOT_FOUND")


def test_R12_ready_route_helper_registers_a_queryable_route(client: TestClient) -> None:
    route_id, token = create_ready_route("fst_000001", "서울역")
    response = client.get(f"{_RETURN}/{route_id}", headers={_TOKEN_HEADER: token})
    ready = _success(response, 200)
    assert ready["route_status"] == "ready"
    assert ready["completed_valid_route"] is True
    assert ready["direction"] == "return"
    assert ready["destination"] == {"type": "place", "label": "서울역"}


def test_R1_reset_store_clears_routes_and_request_ids(client: TestClient) -> None:
    queued = _success(client.post(_RETURN, json=_RETURN_BODY), 202)
    reset_store()
    response = client.get(
        queued["status_url"], headers={_TOKEN_HEADER: queued["route_access_token"]},
    )
    _error(response, 404, "ROUTE_REQUEST_NOT_FOUND")
    _success(client.post(_RETURN, json={**_RETURN_BODY, "destination": {"query": "홍대입구역"}}), 202)


def test_R17_mock_doc() -> None:
    path = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    content = path.read_text(encoding="utf-8")
    for title in ("A04 귀갓길 접수", "A05 귀갓길 조회", "A25 가는 길 접수·조회", "X-Mock-Scenario"):
        assert f"## {title}" in content
    for scenario in ("async_ready", "sync_ready", "async_unavailable", "async_timeout", "overloaded"):
        assert f"| `{scenario}`" in content
    assert "curl -sS -X POST 'http://localhost:8000/api/v1/routes/return'" in content
    assert "curl -sS 'http://localhost:8000/api/v1/routes/return/<route_request_id>'" in content
    assert "X-Route-Access-Token: <route_access_token>" in content
