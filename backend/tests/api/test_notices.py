from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from api.mocks import notices as mock_notices
from api.mocks.store import AccessSession, access_sessions
from api.providers.route_base import KST

ADMIN = "/api/v1/admin/notices"
FESTIVAL = "fst_000001"
PUBLIC = f"/api/v1/festivals/{FESTIVAL}/notices"
ROUTE = "/api/v1/routes/return"


@pytest.fixture
def setup(monkeypatch):
    now = [datetime.now(KST)]
    store = mock_notices.MemoryNoticeStore(lambda: now[0])
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.delenv("NOTICES_PROVIDER", raising=False)
    monkeypatch.setattr(mock_notices, "memory_store", store)
    token = uuid4().hex
    monkeypatch.setenv("MOCK_ADMIN_REVIEW_TOKEN", token)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "festival_id": FESTIVAL, "type": "road_closure", "title": "시험 도로 통제",
        "content": "축제 출입로를 통제합니다.",
        "effective_from": (now[0] + timedelta(seconds=10)).isoformat(),
        "effective_to": (now[0] + timedelta(seconds=20)).isoformat(),
        "source_url": "https://example.test/official",
    }
    return store, now, headers, payload


def test_notice_lifecycle_and_exact_effective_boundaries(client, setup):
    store, now, operator, payload = setup
    register = client.post(ADMIN, json=payload, headers=operator)
    assert register.status_code == 201
    assert register.headers["X-Mock"] == "true"
    assert register.json()["approval_status"] == "pending"
    notice_id = register.json()["notice_id"]
    url = f"{ADMIN}/{notice_id}"
    filter_type = {"type": "road_closure"}
    assert client.get(PUBLIC, params={**filter_type, "active_only": False}).json()["items"] == []

    assert client.post(url + "/end", headers=operator).json()["error"]["code"] == "NOTICE_NOT_APPROVED"
    reviewed = client.post(url + "/review", json={"decision": "approve"}, headers=operator)
    assert reviewed.json() == {"notice_id": notice_id, "approval_status": "approved", "control_version": "cv1"}
    assert client.post(url + "/review", json={"decision": "approve"}, headers=operator).status_code == 409
    assert client.get(PUBLIC, params=filter_type).json()["items"] == []
    assert client.get(PUBLIC, params={**filter_type, "active_only": False}).json()["items"][0]["notice_id"] == notice_id

    assert store.snapshot("fst_000002", now[0]).version == "none"
    now[0] += timedelta(seconds=10)
    item, = client.get(PUBLIC, params=filter_type).json()["items"]
    assert (item["notice_id"], item["source_url"]) == (notice_id, payload["source_url"])
    assert store.snapshot(FESTIVAL, now[0]).version == "cv2"
    now[0] += timedelta(seconds=10)
    assert store.snapshot(FESTIVAL, now[0]).version == "cv3"
    assert client.get(PUBLIC, params=filter_type).json()["items"] == []

    new_end = (now[0] + timedelta(hours=1)).isoformat()
    assert client.patch(url, json={"effective_to": new_end}, headers=operator).json()["approval_status"] == "pending"
    assert store.snapshot(FESTIVAL, now[0]).version == "cv4"
    assert client.get(PUBLIC, params={**filter_type, "active_only": False}).json()["items"] == []
    assert client.post(url + "/review", json={"decision": "approve"}, headers=operator).json()["control_version"] == "cv5"
    assert client.post(url + "/end", json={"reason": "통제 해제"}, headers=operator).json()["control_version"] == "cv6"
    assert client.get(PUBLIC, params=filter_type).json()["items"] == []
    item, = client.get(PUBLIC, params={**filter_type, "active_only": False}).json()["items"]
    assert datetime.fromisoformat(item["effective_to"]) == now[0]
    assert client.post(url + "/end", headers=operator).json()["error"]["code"] == "ALREADY_ENDED"
    assert store.snapshot(FESTIVAL, now[0] + timedelta(hours=1)).version == "cv6"
    assert [event[0] for event in store.events] == ["create", "approve", "update", "approve", "end"]
    assert store.events[2][2].effective_to != store.events[2][3].effective_to
    assert store.events[-1][-1] == "통제 해제"


def test_notice_validates_role_source_period_and_review(client, setup):
    store, _, operator, payload = setup
    assert client.post(ADMIN, json=payload).status_code == 401
    token = uuid4().hex
    access_sessions[token] = AccessSession(str(uuid4()), datetime.now(KST) + timedelta(minutes=1))
    regular = {"Authorization": f"Bearer {token}"}
    assert client.post(ADMIN, json=payload, headers=regular).status_code == 403
    for key, value in (
        ("source_url", None), ("source_url", "ftp://example.test"), ("effective_from", "2026-11-24T22:00"),
        ("effective_from", 1800000000), ("effective_to", payload["effective_from"]), ("type", "construction"),
    ):
        response = client.post(ADMIN, json={**payload, key: value}, headers=operator)
        assert response.status_code == 422
    missing_source = {key: value for key, value in payload.items() if key != "source_url"}
    assert client.post(ADMIN, json=missing_source, headers=operator).status_code == 422
    assert client.post(ADMIN, json={**payload, "festival_id": "fst_missing"}, headers=operator).status_code == 404
    assert client.patch(f"{ADMIN}/ntc_missing", json={"title": "수정"}, headers=operator).status_code == 404

    notice_id = client.post(ADMIN, json=payload, headers=operator).json()["notice_id"]
    url = f"{ADMIN}/{notice_id}"
    for patch in ({}, {"source_url": None}, {"effective_to": payload["effective_from"]}):
        assert client.patch(url, json=patch, headers=operator).status_code == 422
    assert client.post(url + "/review", json={"decision": "reject"}, headers=operator).status_code == 422
    response = client.post(url + "/review", json={"decision": "reject", "reason": "시각 재확인"}, headers=operator)
    assert response.json()["control_version"] is None
    assert response.json()["approval_status"] == "rejected"
    assert len(store.events) == 2
    assert client.get(PUBLIC, params={"type": "road_closure", "active_only": False}).json()["items"] == []


def test_mock_route_replay_observes_common_control_and_keeps_request_id(client, setup):
    store, now, operator, payload = setup
    body = {"request_id": "notice-route-fixture", "festival_id": FESTIVAL,
            "destination": {"lat": 37.5, "lng": 126.9}}
    ready = client.post(ROUTE, json=body, headers={"X-Mock-Scenario": "sync_ready"}).json()
    notice_id = client.post(ADMIN, json={**payload, "festival_id": None}, headers=operator).json()["notice_id"]
    client.post(f"{ADMIN}/{notice_id}/review", json={"decision": "approve"}, headers=operator)
    now[0] += timedelta(seconds=10)
    assert store.snapshot("fst_000002", now[0]).version == "cv2"
    other_notices = client.get("/api/v1/festivals/fst_000002/notices", params={"type": "road_closure"}).json()
    assert other_notices["items"][0]["notice_id"] == notice_id

    replay = client.post(ROUTE, json=body, headers={"X-Mock-Scenario": "sync_ready"}).json()
    assert replay["route_request_id"] == ready["route_request_id"]
    assert replay["error"]["code"] == "ROUTE_CONTROL_CHANGED"
    changed = client.post(ROUTE, json={**body, "route_preference": "less_crowded"})
    assert changed.status_code == 409
    fresh = client.post(ROUTE, json={**body, "request_id": "notice-route-fresh"},
                        headers={"X-Mock-Scenario": "sync_ready"}).json()
    assert fresh["route_status"] == "ready"
    assert fresh["verification_status"] == "control_unverified"
    assert PUBLIC in fresh["notices"][0] and payload["title"] in fresh["notices"][0]
