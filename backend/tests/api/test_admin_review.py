from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest

from api.mocks.festival_review import MemoryReviewStore
from api.mocks.store import AccessSession, access_sessions
from api.routers.admin import festival_review

PATH = "/api/v1/admin/festivals/review-queue"


@pytest.fixture
def operator(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    token = uuid4().hex
    monkeypatch.setenv("MOCK_ADMIN_REVIEW_TOKEN", token)
    monkeypatch.setattr(festival_review, "_mock_store", MemoryReviewStore())
    return {"Authorization": f"Bearer {token}"}


def test_roles_filters_pagination_and_mock_marker(client, operator):
    assert client.get(PATH).status_code == 401
    regular_token = uuid4().hex
    access_sessions[regular_token] = AccessSession(
        str(uuid4()), datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    regular = {"Authorization": f"Bearer {regular_token}"}
    assert client.get(PATH, headers=regular).status_code == 403
    assert client.post(PATH, headers=regular, json={
        "queue_id": 1, "decision": "approve", "note": "검토 완료",
    }).status_code == 403

    response = client.get(PATH, headers=operator, params={"page": 2, "page_size": 2})
    assert response.status_code == 200 and response.headers["X-Mock"] == "true"
    data = response.json()
    assert (data["page"], data["page_size"], data["total"]) == (2, 2, 6)
    assert [item["queue_id"] for item in data["items"]] == [4, 3]
    for reason in ("duplicate", "conflict", "not_festival_class", "class_unverified",
                   "missing_from_source", "coords_out_of_range"):
        rows = client.get(PATH, headers=operator, params={"reason": reason}).json()
        assert rows["total"] == 1 and rows["items"][0]["reason"] == reason
    for params in ({"reason": "unknown"}, {"page": 0}, {"page_size": 101}, {"approval_status": "hidden"}):
        assert client.get(PATH, headers=operator, params=params).status_code == 422


@pytest.mark.parametrize("payload", [
    {"queue_id": 1, "decision": "reject"},
    {"queue_id": 1, "decision": "hide", "note": "  "},
    {"queue_id": 1, "decision": "reject", "note": "가" * 201},
    {"queue_id": 2**63, "decision": "approve", "note": "검토"},
    {"queue_id": 3, "decision": "approve", "note": "공연"},
    {"queue_id": 4, "decision": "approve", "note": "미분류"},
    {"queue_id": 6, "decision": "approve", "note": "주소 있음"},
    {"queue_id": 6, "decision": "approve", "note": "좌표 오류", "value": {"latitude": 40, "longitude": 127}},
    {"queue_id": 1, "decision": "approve", "note": "서버 상태 필드", "value": {"published_at": "2026-11-24"}},
    {"queue_id": 1, "decision": "approve", "note": "좌표 한쪽만", "value": {"latitude": 37}},
    {"queue_id": 1, "decision": "approve", "note": "좌표 출처만", "value": {"coords_source": "geocoded"}},
])
def test_invalid_decisions_leave_queue_pending(client, operator, payload):
    response = client.post(PATH, headers=operator, json=payload)
    assert response.status_code == 422 and response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get(PATH, headers=operator).json()["total"] == 6


def test_decisions_and_retry_error(client, operator):
    cases = [
        (1, "approve", None, "approved", True),
        (2, "reject", None, "rejected", False),
        (5, "hide", None, "rejected", True),
        (6, "approve", {"latitude": 37.5, "longitude": 127.1, "coords_source": "geocoded"}, "approved", True),
    ]
    for queue_id, decision, value, status, applied in cases:
        payload = {"queue_id": queue_id, "decision": decision, "reason": "검토 완료", "value": value}
        assert client.post(PATH, headers=operator, json=payload).json() == {
            "queue_id": queue_id, "approval_status": status, "applied": applied,
        }
        retry = client.post(PATH, headers=operator, json=payload)
        assert retry.status_code == 409 and retry.json()["error"]["code"] == "ALREADY_REVIEWED"
    assert client.get(PATH, headers=operator, params={"approval_status": "approved"}).json()["total"] == 2
    assert client.get(PATH, headers=operator, params={"approval_status": "rejected"}).json()["total"] == 2
    missing = client.post(PATH, headers=operator, json={"queue_id": 100, "decision": "hide", "note": "검토"})
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "QUEUE_ITEM_NOT_FOUND"


def test_memory_store_processes_same_item_once(client, operator):
    barrier = Barrier(2, timeout=5)

    def decide(action):
        barrier.wait()
        return client.post(PATH, headers=operator, json={"queue_id": 1, "decision": action, "note": "검토"})

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(response.status_code for response in pool.map(decide, ("approve", "hide"))) == [200, 409]
