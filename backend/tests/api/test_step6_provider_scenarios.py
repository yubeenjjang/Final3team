from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

_SCENARIO_HEADER = "X-Mock-Scenario"
_TOKEN_HEADER = "X-Route-Access-Token"
_SECONDARY_CODE = "ROUTE_SECONDARY_SYNC_ONLY"
_SECONDARY_MESSAGE = "잠시 뒤 다시 조회해 주세요."


@pytest.fixture(params=["return", "visit"])
def route(request: pytest.FixtureRequest) -> tuple[str, dict[str, object]]:
    direction = request.param
    place_field = "destination" if direction == "return" else "origin"
    return f"/api/v1/routes/{direction}", {
        "request_id": "step6-request-01",
        "festival_id": "fst_000001",
        place_field: {"query": "서울역"},
    }


def _success(response: Response, status: int) -> dict[str, Any]:
    assert response.status_code == status
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    return body


def _poll(client: TestClient, url: str, token: str) -> dict[str, Any]:
    return _success(client.get(url, headers={_TOKEN_HEADER: token}), 200)


def _assert_unavailable(
    body: dict[str, Any], route_id: str, code: str, message: str, *, retryable: bool
) -> None:
    assert body == {
        "route_request_id": route_id,
        "route_status": "unavailable",
        "completed_valid_route": False,
        "updated_at": body["updated_at"],
        "is_mock": True,
        "error": {"code": code, "message": message, "retryable": retryable},
        "notices": [message],
    }
    assert body["completed_valid_route"] is False
    assert body["error"]["retryable"] is retryable


def test_R23_secondary_result_is_only_available_on_submit(
    client: TestClient, route: tuple[str, dict[str, object]]
) -> None:
    url, body = route
    ready = _success(client.post(url, json=body, headers={_SCENARIO_HEADER: "sync_secondary"}), 200)
    mock = _success(
        client.post(
            url, json={**body, "request_id": "step6-request-mock"},
            headers={_SCENARIO_HEADER: "sync_ready"},
        ),
        200,
    )
    assert ready["completed_valid_route"] is True
    assert ready["direction"] == url.rsplit("/", 1)[-1]
    assert "route_access_token" not in ready
    assert "route_access_token" not in mock
    assert len(ready["route_candidates"]) == 1
    for candidate in mock["route_candidates"]:
        candidate["mode_evidence"]["bus_crowding"] = {
            "status": "unsupported",
            "reason": "2차 공급원은 버스 혼잡 근거를 주지 않아요(모의)",
        }
    assert ready == {
        **mock,
        "route_request_id": ready["route_request_id"],
        "queried_at": ready["queried_at"],
        "provider": "kakao",
        "provider_tier": "secondary",
        "notices": [
            "공식 교통통제 반영 여부를 확인하지 못했어요.",
            "2차 공급원(카카오맵) 결과예요. 이 결과는 저장하지 않아 다시 보려면 새로 조회해야 해요.",
        ],
    }

    status_url = f"{url}/{ready['route_request_id']}"
    assert client.get(status_url).status_code == 401
    assert _success(client.post(url, json=body), 200) == ready


def _finish_async(
    client: TestClient, route: tuple[str, dict[str, object]], scenario: str
) -> dict[str, Any]:
    url, body = route
    queued = _success(client.post(url, json=body, headers={_SCENARIO_HEADER: scenario}), 202)
    assert queued["route_status"] == "queued"
    assert queued["status_url"] == f"{url}/{queued['route_request_id']}"
    assert queued["retry_after_s"] == 2
    status_url, token = queued["status_url"], queued["route_access_token"]
    processing = _poll(client, status_url, token)
    assert processing["route_status"] == "processing"
    assert processing["completed_valid_route"] is False
    assert processing["retry_after_s"] == 2
    failed = _poll(client, status_url, token)
    assert failed["route_request_id"] == queued["route_request_id"]
    assert _poll(client, status_url, token) == failed
    return failed


def test_R24_async_secondary_sync_only(
    client: TestClient, route: tuple[str, dict[str, object]]
) -> None:
    failed = _finish_async(client, route, "async_secondary_sync_only")
    _assert_unavailable(
        failed, failed["route_request_id"], _SECONDARY_CODE, _SECONDARY_MESSAGE, retryable=True,
    )


@pytest.mark.parametrize(
    ("scenario", "code", "message"),
    [
        ("async_no_result", "ROUTE_NO_RESULT", "조건에 맞는 경로가 없어요."),
        (
            "async_quota_exceeded",
            "ROUTE_QUOTA_EXCEEDED",
            "오늘 조회 한도를 다 썼어요. 공식 교통 안내를 확인해 주세요.",
        ),
    ],
)
def test_R25_async_route_failure_is_not_retryable(
    client: TestClient, route: tuple[str, dict[str, object]], scenario: str, code: str, message: str
) -> None:
    failed = _finish_async(client, route, scenario)
    _assert_unavailable(failed, failed["route_request_id"], code, message, retryable=False)


def test_R26_provider_scenarios_are_documented() -> None:
    path = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    section = path.read_text(encoding="utf-8").split("## X-Mock-Scenario\n", 1)[1]
    table = section.strip().split("\n\n")[1]
    for scenario, code in (
        ("sync_secondary", _SECONDARY_CODE),
        ("async_secondary_sync_only", _SECONDARY_CODE),
        ("async_no_result", "ROUTE_NO_RESULT"),
        ("async_quota_exceeded", "ROUTE_QUOTA_EXCEEDED"),
    ):
        assert any(row.startswith(f"| `{scenario}` |") and code in row for row in table.splitlines())
