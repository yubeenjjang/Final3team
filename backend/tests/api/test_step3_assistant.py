import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

RUNS = "/api/v1/assistant/runs"


def _start(client: TestClient, **fields: object) -> dict:
    response = client.post(RUNS, json={"request_id": "assistant-001", "message": "축제 알려줘", **fields})
    assert response.status_code == 202
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    return body


def _poll(client: TestClient, run: dict) -> dict:
    response = client.get(run["status_url"], headers={"X-Run-Access-Token": run["run_access_token"]})
    assert response.status_code == 200
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    return body


def test_R14_accepted_and_idempotent(client: TestClient) -> None:
    run = _start(client)
    assert re.fullmatch(r"run_[0-9A-Za-z]{16}", run["run_id"])
    assert re.fullmatch(r"cv_[0-9A-Za-z]{16}", run["conversation_id"])
    assert re.fullmatch(r"rat_[0-9A-Za-z]{24}", run["run_access_token"])
    assert run["run_status"] == "queued"
    assert run["status_url"] == f"{RUNS}/{run['run_id']}"
    assert run["events_url"] == f"{run['status_url']}/events"
    assert run["retry_after_s"] == 1

    _poll(client, run)
    assert _start(client) == run
    conflict = client.post(RUNS, json={"request_id": "assistant-001", "message": "다른 질문"})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.parametrize(
    ("fields", "invalid_field"),
    [
        ({"message": ""}, "message"),
        ({"message": "가" * 501}, "message"),
        ({"request_id": "짧음"}, "request_id"),
        ({"conversation_id": "invalid"}, "conversation_id"),
        ({"context": {"festival_id": "wrong"}}, "context.festival_id"),
        ({"context": {"route_request_id": "wrong"}}, "context.route_request_id"),
        ({"reference_date": "2026-02-30"}, "reference_date"),
        ({"reference_date": "20261122"}, "reference_date"),
    ],
)
def test_R14_invalid_input(client: TestClient, fields: dict, invalid_field: str) -> None:
    response = client.post(RUNS, json={"request_id": "assistant-001", "message": "축제", **fields})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert invalid_field in error["message"]


def test_R14_existing_and_unknown_conversation(client: TestClient) -> None:
    first = _start(client)
    second = _start(
        client,
        request_id="assistant-002",
        conversation_id=first["conversation_id"],
        context={"festival_id": "fst_zzzzzz", "route_request_id": "rr_zzzzzz"},
        reference_date="2026-11-22",
    )
    assert second["conversation_id"] == first["conversation_id"]
    assert second["run_id"] != first["run_id"]
    response = client.post(
        RUNS, json={"request_id": "assistant-003", "message": "축제", "conversation_id": "cv_zzzzzz"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_R15_running_then_succeeded(client: TestClient) -> None:
    run = _start(client)
    running = _poll(client, run)
    assert running == {
        "run_id": run["run_id"],
        "conversation_id": run["conversation_id"],
        "run_status": "running",
        "run_kind": "chat",
        "answer": None,
        "used_tools": [],
        "evidence": [],
        "result": None,
        "route_request_id": None,
        "route_access_token": None,
        "error": None,
        "queued_at": running["queued_at"],
        "started_at": running["started_at"],
        "ended_at": None,
        "is_mock": True,
    }
    assert running["queued_at"] <= running["started_at"]

    done = _poll(client, run)
    assert done["run_status"] == "succeeded"
    assert done["answer"] == "이번 주 서울에서 열리는 축제는 광화문 겨울빛 축제예요.(모의)"
    assert done["used_tools"] == [{"tool": "search_festivals", "ok": True, "error_code": None}]
    (evidence,) = done["evidence"]
    assert evidence["type"] == "festival"
    assert evidence["ref"] == "fst_000001"
    assert evidence["provider"] == "tourapi"
    assert datetime.fromisoformat(evidence["queried_at"]).tzinfo is not None
    assert running["started_at"] <= done["ended_at"]
    assert _poll(client, run) == done


def test_R15_failure(client: TestClient) -> None:
    run = _start(client, message="귀가 실패")
    assert _poll(client, run)["run_status"] == "running"
    done = _poll(client, run)
    assert done["run_status"] == "failed"
    assert done["answer"] is None
    assert done["error"] == {
        "code": "AI_AGENT_FAILED",
        "message": "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요.",
        "retryable": True,
    }
    assert done["used_tools"] == [{"tool": "request_return_route", "ok": False, "error_code": "TOOL_TIMEOUT"}]


@pytest.mark.parametrize(
    ("message", "context", "expected_festival"),
    [
        ("귀가하고 싶어", {}, "fst_000001"),
        ("돌아가는 방법 알려줘", {"festival_id": "fst_000002"}, "fst_000002"),
        ("가는 길 알려줘", {}, "fst_000001"),
    ],
)
def test_R15_route_is_ready(
    client: TestClient, message: str, context: dict[str, str], expected_festival: str
) -> None:
    run = _start(client, message=message, context=context)
    assert _poll(client, run)["run_status"] == "running"
    done = _poll(client, run)
    route_id = done["route_request_id"]
    assert done["run_status"] == "succeeded"
    assert done["answer"] == "경로를 찾았어요. 귀가 화면에서 확인하세요."
    (evidence,) = done["evidence"]
    assert evidence["type"] == "route"
    assert evidence["ref"] == route_id
    assert evidence["provider"] == "mock_adapter"
    assert datetime.fromisoformat(evidence["queried_at"]).tzinfo is not None
    assert done["used_tools"] == [
        {"tool": "get_festival", "ok": True, "error_code": None},
        {"tool": "request_return_route", "ok": True, "error_code": None},
    ]
    response = client.get(
        f"/api/v1/routes/return/{route_id}",
        headers={"X-Route-Access-Token": done["route_access_token"]},
    )
    assert response.status_code == 200
    route = response.json()
    assert route["route_status"] == "ready"
    assert route["festival_id"] == expected_festival
    assert route["is_mock"] is True
    assert _poll(client, run) == done


def test_R15_missing_or_wrong_token_and_missing_run(client: TestClient) -> None:
    first = _start(client)
    second = _start(client, request_id="assistant-002")
    wrong_token = {"X-Run-Access-Token": second["run_access_token"]}
    for path, headers, status, code in (
        (first["status_url"], {}, 401, "UNAUTHORIZED"),
        (first["status_url"], wrong_token, 403, "FORBIDDEN"),
        (f"{RUNS}/run_zzzzzzzz", wrong_token, 404, "RUN_NOT_FOUND"),
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == status
        assert response.json()["error"]["code"] == code
    assert _poll(client, first)["run_status"] == "running"


@pytest.mark.parametrize(
    ("festival_id", "route_error"),
    [("fst_zzzzzz", "FESTIVAL_NOT_FOUND"), ("fst_000006", "FESTIVAL_LOCATION_UNKNOWN")],
)
def test_R15_route_error_still_returns_terminal_state(
    client: TestClient, festival_id: str, route_error: str
) -> None:
    run = _start(client, message="귀가", context={"festival_id": festival_id})
    assert _poll(client, run)["run_status"] == "running"
    done = _poll(client, run)
    assert done["run_status"] == "failed"
    assert done["error"]["code"] == "AI_AGENT_FAILED"
    assert done["used_tools"][0]["error_code"] == route_error
    assert done["route_request_id"] is None
    assert _poll(client, run) == done
