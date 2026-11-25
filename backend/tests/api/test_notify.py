from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from api.services import mock_chat, mock_reports

from .test_chat import INBOX, ROOMS, connect_url, send, signup
from .test_chat import mock as mock_chat_state
from .test_companions import APPLICATIONS, POSTS, clock, post_body
from .test_friends import act as friend_act
from .test_friends import send as friend_send

REPORTS = "/api/v1/reports"
ADMIN = "/api/v1/admin/reports"
SUMMARY_FIELDS = {"report_id", "target_type", "target_id", "reason", "status", "created_at"}


@pytest.fixture
def review(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.setattr(mock_reports, "mock_reports", mock_reports.MemoryReports())
    token = "fixture-mock-report-review-token-for-test"
    monkeypatch.setenv("MOCK_ADMIN_REPORTS_TOKEN", token)
    return {"Authorization": f"Bearer {token}"}


def submit(client, headers, kind, target, **changes):
    return client.post(REPORTS, headers=headers, json={
        "target_type": kind, "target_id": str(target), "reason": "abuse", **changes,
    })


def decide(client, reviewer, report_id, action):
    return client.post(ADMIN, headers=reviewer, json={"report_id": report_id, "action": action, "note": "검토 완료"})


def test_notification_workflows_and_retention(client, mock_chat_state, clock, monkeypatch):
    (alice, a), (bob, b), (carol, c) = (signup(client, i) for i in range(3))
    request = friend_send(client, a, bob).json()["request_id"]
    assert friend_act(client, b, request, "accept").status_code == 200
    crossed = friend_send(client, a, carol).json()
    assert crossed["status"] == "pending"
    assert friend_send(client, c, alice).json() == {"request_id": crossed["request_id"], "status": "accepted"}
    room = client.post(ROOMS, headers=a, json={
        "type": "friend_group", "name": "친구들", "invitee_ids": [bob, carol],
    }).json()["room_id"]
    assert client.post(f"{ROOMS}/{room}/invitations", headers=a, json={"invitee_ids": [bob]}).json()["invited"] == []

    post = client.post(POSTS, headers=a, json=post_body()).json()["post_id"]
    application = client.post(f"{POSTS}/{post}/applications", headers=b).json()["application_id"]
    assert client.post(f"{APPLICATIONS}/{application}/approve", headers=a).status_code == 200
    owner = client.get(INBOX, headers=a).json()
    guest = client.get(INBOX, headers=b).json()
    assert [(row["type"], row["ref_id"]) for row in owner["items"]] == [
        ("companion_applied", application), ("friend_accepted", crossed["request_id"]),
        ("friend_accepted", request),
    ]
    assert [(row["type"], row["ref_id"]) for row in guest["items"]] == [
        ("companion_approved", application), ("room_invited", room), ("friend_requested", request),
    ]
    assert client.post(f"{INBOX}/read", headers=b, json={"ids": [owner["items"][0]["notification_id"]]}).status_code == 204
    assert client.get(INBOX, headers=a).json()["unread_count"] == 3
    assert client.post(f"{INBOX}/read", headers=a, json={"ids": [owner["items"][0]["notification_id"]]}).status_code == 204
    assert client.get(INBOX, headers=a, params={"unread_only": True}).json()["unread_count"] == 2
    monkeypatch.setattr(mock_chat, "now", lambda: datetime.now(timezone.utc) + timedelta(days=90))
    assert client.get(INBOX, headers=a).json() == {"items": [], "unread_count": 0}


def test_chat_report_scope_audit_and_moderation(client, mock_chat_state, review):
    (alice, a), (bob, b), (carol, c), (_, outsider) = (signup(client, i) for i in range(4))
    for peer, peer_headers in ((bob, b), (carol, c)):
        request = friend_send(client, a, peer).json()["request_id"]
        assert friend_act(client, peer_headers, request, "accept").status_code == 200
    room = client.post(ROOMS, headers=a, json={
        "type": "friend_group", "name": "신고 시험방", "invitee_ids": [bob, carol],
    }).json()["room_id"]
    assert submit(client, b, "chat_room", room).status_code == 404
    assert submit(client, outsider, "chat_room", room).status_code == 404
    with client.websocket_connect(connect_url(client, a)) as socket:
        before = send(socket, room, "report-01", "입장 전")["message_id"]
        assert client.post(f"{ROOMS}/{room}/accept", headers=b).status_code == 200
        message = send(socket, room, "report-02", "신고 대상")["message_id"]
        other = send(socket, room, "report-03", "같은 방의 다른 원문")["message_id"]
    assert submit(client, b, "chat_message", before).status_code == 404
    assert submit(client, outsider, "chat_message", message).status_code == 404

    room_report = submit(client, b, "chat_room", room).json()["report_id"]
    message_report = submit(client, b, "chat_message", message).json()["report_id"]
    assert submit(client, b, "chat_message", f"0{message}").status_code == 409
    assert client.get(ADMIN).status_code == 401
    assert client.get(ADMIN, headers=a, params={"report_id": message_report}).status_code == 403
    assert client.get(REPORTS, headers=a).status_code == 405

    page = client.get(ADMIN, headers=review, params={"status": "received"}).json()
    assert {row["report_id"] for row in page["items"]} == {room_report, message_report}
    assert all(set(row) == SUMMARY_FIELDS for row in page["items"])
    assert mock_reports.mock_reports._access == []

    room_view = client.get(ADMIN, headers=review, params={"report_id": room_report})
    assert room_view.headers["Cache-Control"] == "private, no-store"
    assert room_view.json()["room"] == {"room_id": room, "room_type": "friend_group", "name": "신고 시험방", "status": "active"}
    assert room_view.json()["message"] is None
    assert room_view.json()["report"]["status"] == "reviewing"
    message_view = client.get(ADMIN, headers=review, params={"report_id": message_report}).json()
    assert set(message_view) == {"report", "room", "message", "access_id"}
    assert set(message_view["message"]) == {"message_id", "seq", "sender_id", "body", "created_at"}
    assert message_view["message"]["sender_id"] == alice
    assert message_view["message"]["body"] == "신고 대상"
    assert message_view["message"]["message_id"] == message
    repeated = client.get(ADMIN, headers=review, params={"report_id": message_report}).json()
    assert repeated["access_id"] > message_view["access_id"] > room_view.json()["access_id"]
    assert [row.report_id for row in mock_reports.mock_reports._access] == [room_report, message_report, message_report]

    assert decide(client, review, message_report, "close_room").status_code == 403
    result = decide(client, review, message_report, "hide_message").json()
    assert set(result) == {"report_id", "status", "handled_by", "handled_at"}
    assert result["status"] == "actioned"
    assert decide(client, review, message_report, "dismiss").status_code == 403
    assert [row["message_id"] for row in client.get(f"{ROOMS}/{room}/messages", headers=b).json()["items"]] == [other]
    assert decide(client, review, room_report, "close_room").json()["status"] == "actioned"
    assert client.get(ADMIN, headers=review, params={"report_id": room_report}).json()["room"]["status"] == "read_only"


def test_daily_limit_and_non_chat_actions(client, review, clock, mock_chat_state, monkeypatch):
    (_, a), (bob, b), (_, c) = (signup(client, i) for i in range(3))
    timestamp = [datetime(2026, 11, 24, 14, 59, tzinfo=timezone.utc)]
    monkeypatch.setattr(mock_reports, "now", lambda: timestamp[0])
    assert submit(client, a, "user", bob, reason="unknown").status_code == 422
    assert submit(client, a, "user", bob, detail="x" * 501).status_code == 422
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: submit(client, a, "user", bob.upper()), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert submit(client, c, "user", bob).status_code == 201
    timestamp[0] += timedelta(minutes=1)
    response = submit(client, a, "user", bob)
    assert response.status_code == 201
    user_report = response.json()["report_id"]
    evidence = client.get(ADMIN, headers=review, params={"report_id": user_report}).json()
    assert evidence["message"] is evidence["room"] is evidence["access_id"] is None
    assert decide(client, review, user_report, "block_user").json()["status"] == "actioned"
    assert client.get(INBOX, headers=b).status_code == 401

    post = client.post(POSTS, headers=a, json=post_body()).json()["post_id"]
    post_report = submit(client, c, "companion_post", post).json()["report_id"]
    assert decide(client, review, post_report, "hide_post").json()["status"] == "actioned"
    assert client.get(f"{POSTS}/{post}", headers=c).status_code == 404
    assert client.get(f"{POSTS}/{post}", headers=a).status_code == 200
    another = submit(client, a, "companion_post", post).json()["report_id"]
    assert decide(client, review, another, "dismiss").json()["status"] == "dismissed"


def test_cannot_report_own_account(client, review):
    uid, headers = signup(client, 0)
    rejected = submit(client, headers, "user", uid.upper())
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get(ADMIN, headers=review).json()["items"] == []


@pytest.mark.parametrize("role", ["operator", "admin"])
def test_report_moderation_rejects_staff_before_updating_account(role):
    from unittest.mock import Mock
    from uuid import uuid4

    from api.errors import ApiError
    from api.repositories.reports import _apply_action

    db = Mock()
    db.scalar.side_effect = [1, role]
    with pytest.raises(ApiError) as denied:
        _apply_action(db, str(uuid4()), "block_user", uuid4())
    assert (denied.value.status, denied.value.code) == (403, "FORBIDDEN")
    db.execute.assert_not_called()
