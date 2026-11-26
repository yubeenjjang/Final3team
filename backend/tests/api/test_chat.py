import logging
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from starlette.websockets import WebSocketDisconnect

from api.realtime import chat_socket
from api.request_logs import _PrivateRequestFilter
from api.services import mock_chat
from api.services.chat import ChatIdentity, ChatRooms

BASE = "/api/v1"
ROOMS = f"{BASE}/chat-rooms"
INBOX = f"{BASE}/me/notifications"
LIST = f"{BASE}/me/chat-rooms"


@pytest.fixture
def mock(client, monkeypatch):
    monkeypatch.delenv("AUTH_PROVIDER", raising=False)
    store = mock_chat.MockChatRooms()
    monkeypatch.setattr(mock_chat, "mock_rooms", store)
    monkeypatch.setattr(chat_socket, "tickets", chat_socket.MemoryTickets())
    monkeypatch.setattr(chat_socket, "bus", chat_socket.MemoryChatBus())
    monkeypatch.setattr(chat_socket, "limits", chat_socket.MessageLimits(clock=lambda: 2.0))
    return store


def signup(client, index):
    response = client.post(f"{BASE}/auth/signup", json={
        "email": f"user{index}@example.test", "password": "MockChatPassword123",
        "display_name": f"채팅사용자{index}", "birth_year": 2000, "gender": "female",
    })
    assert response.status_code == 201
    login = client.post(f"{BASE}/auth/login", json={
        "email": f"user{index}@example.test", "password": "MockChatPassword123",
    })
    assert login.status_code == 200
    result = login.json()
    return result["user"]["user_id"], {"Authorization": f"Bearer {result['access_token']}"}


def connect_url(client, headers):
    response = client.post(f"{BASE}/ws-tickets", headers=headers, json={})
    assert response.status_code == 201
    assert response.headers["Cache-Control"] == "no-store"
    assert response.json()["expires_in"] == 30
    return f"{BASE}/ws/chat?ticket={response.json()['ticket']}"


def send(ws, room, client_id, body):
    ws.send_json({"type": "send", "room_id": room, "client_message_id": client_id, "body": body})
    return ws.receive_json()


def subscribe(ws, room, seq):
    ws.send_json({"type": "subscribe", "room_id": room, "after_seq": seq})


def test_mock_group_invite_membership_history_and_notifications(client, mock):
    (alice, a), (bob, b), (carol, c), (dan, d) = (signup(client, i) for i in range(4))
    mock.friendships.update(frozenset((UUID(alice), UUID(other))) for other in (bob, carol, dan))
    with client.websocket_connect(connect_url(client, b)) as guest:
        creation = client.post(ROOMS, headers=a, json={
            "type": "friend_group", "name": "친구들", "invitee_ids": [bob, carol],
        })
        room = creation.json()["room_id"]
        path = f"{ROOMS}/{room}"
        assert creation.status_code == 201 and creation.headers["X-Mock"] == "true"
        alert = guest.receive_json()
        assert alert["type"] == "notification"
        assert alert["notification"]["type"] == "room_invited"
        assert alert["notification"]["ref_id"] == room
        assert client.get(INBOX, headers=a).json() == {"items": [], "unread_count": 0}
        assert client.post(f"{INBOX}/read", headers=a, json={"ids": [alert["notification"]["notification_id"]]}).status_code == 204
        assert client.get(INBOX, headers=b).json()["unread_count"] == 1
        assert client.post(f"{INBOX}/read", headers=b, json={"all": True}).status_code == 204
        assert client.get(INBOX, headers=b, params={"unread_only": True}).json() == {"items": [], "unread_count": 0}
        assert client.get(LIST, headers=b).json()["items"][0]["my_status"] == "invited"
        subscribe(guest, room, 0)
        assert guest.receive_json() == {"type": "error", "code": "FORBIDDEN"}
        assert send(guest, room, "msg-0001", "초대 상태")["code"] == "FORBIDDEN"
        assert client.get(f"{path}/messages", headers=d).status_code == 403
        with client.websocket_connect(connect_url(client, a)) as owner:
            ack = send(owner, room, "msg-0001", "입장 전")
            assert ack["type"] == "ack" and ack["seq"] == 1
            assert send(owner, room, "msg-0001", "재전송") == ack
            assert client.post(f"{path}/accept", headers=b).json()["my_status"] == "joined"
            assert client.post(f"{path}/decline", headers=c).json()["my_status"] == "declined"
            assert client.post(f"{path}/accept", headers=c).status_code == 409
            assert client.get(f"{path}/messages", headers=b).json() == {"items": [], "has_more": False}
            subscribe(guest, room, 0)
            assert send(owner, room, "msg-0002", "입장 후")["seq"] == 2
            assert guest.receive_json()["seq"] == 2
            assert send(owner, room, "msg-0003", "세 번째")["seq"] == 3
            assert guest.receive_json()["seq"] == 3
            page = client.get(f"{path}/messages", headers=b, params={"before_seq": 4, "limit": 1}).json()
            assert page["has_more"] and [row["seq"] for row in page["items"]] == [3]
            page = client.get(f"{path}/messages", headers=b, params={"after_seq": 0, "limit": 1}).json()
            assert page["has_more"] and page["items"][0]["sender_display_name"] == "채팅사용자0"
            assert [row["seq"] for row in page["items"]] == [2]
            assert client.get(LIST, headers=b).json()["items"][0]["unread_count"] == 2
            assert client.post(f"{path}/read", headers=b, json={"seq": 3}).status_code == 204
            assert client.post(f"{path}/read", headers=b, json={"seq": 1}).status_code == 204
            assert client.get(LIST, headers=b).json()["items"][0]["unread_count"] == 0
            assert client.patch(path, headers=b, json={"name": "다른 이름"}).status_code == 403
            invitation = client.post(f"{path}/invitations", headers=a, json={"invitee_ids": [bob, dan]}).json()
            assert [row["user_id"] for row in invitation["invited"]] == [dan]
            assert client.post(f"{path}/accept", headers=d).status_code == 200
            subscribe(owner, room, 3)
            owner.send_text("bad json")
            assert owner.receive_json()["code"] == "VALIDATION_ERROR"
            assert client.post(f"{path}/leave", headers=a).json()["my_status"] == "left"
            assert owner.receive_json() == {"type": "unsubscribed", "room_id": room, "reason": "left"}
            assert client.patch(path, headers=d, json={"name": "다른 이름"}).status_code == 403
            assert client.patch(path, headers=b, json={"name": "새 이름"}).json() == {"room_id": room, "name": "새 이름"}
        assert client.get(f"{path}/messages", headers=a).status_code == 403

    with client.websocket_connect(connect_url(client, b)) as reconnected:
        subscribe(reconnected, room, 2)
        replayed = reconnected.receive_json()
        assert (replayed["type"], replayed["seq"], replayed["body"]) == ("message", 3, "세 번째")
        assert "sender_display_name" not in replayed


def test_mock_direct_room_block_and_reopen(client, mock):
    (alice, a), (bob, b) = (signup(client, i) for i in range(2))
    params = {"type": "direct", "friend_id": bob}
    assert client.post(ROOMS, headers=a, json=params).json()["error"]["code"] == "NOT_FRIENDS"
    mock.friendships.add(frozenset((UUID(alice), UUID(bob))))
    r = client.post(ROOMS, headers=a, json=params)
    assert r.status_code == 201
    room = r.json()["room_id"]
    reverse = client.post(ROOMS, headers=b, json={"type": "direct", "friend_id": alice})
    assert reverse.status_code == 200 and reverse.json()["room_id"] == room

    with client.websocket_connect(connect_url(client, a)) as ws:
        subscribe(ws, room, 0)
        assert send(ws, room, "msg-0001", "처음 방")["seq"] == 1
        assert ws.receive_json()["type"] == "message"
        mock.blocks.add((UUID(bob), UUID(alice)))
        assert client.post(ROOMS, headers=a, json=params).json()["error"]["code"] == "BLOCKED"
        assert send(ws, room, "msg-0002", "차단")["code"] == "FORBIDDEN"
        ChatRooms.close_direct_room_on_unblock(UUID(alice), UUID(bob))
        mock.blocks.clear()
        assert ws.receive_json() == {"type": "room_status", "room_id": room, "status": "closed"}
        assert ws.receive_json() == {"type": "unsubscribed", "room_id": room, "reason": "blocked"}
    assert client.get(f"{ROOMS}/{room}/messages", headers=b).status_code == 403
    new = client.post(ROOMS, headers=a, json=params)
    assert new.status_code == 201 and new.json()["room_id"] != room


def test_tickets_expire_once_and_redact_query(client, mock):
    user_id, headers = signup(client, 0)
    url = connect_url(client, headers)
    with client.websocket_connect(url):
        pass
    with client.websocket_connect(url) as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    assert exc.value.code == 4401
    clock = [1.0]
    store = chat_socket.MemoryTickets(lambda: clock[0])
    token = store.issue(ChatIdentity(UUID(user_id)))
    assert all(token not in key for key in store.entries)
    clock[0] += 30
    assert store.consume(token) is None
    record = logging.LogRecord("uvicorn.error", logging.INFO, "protocol", 1, "%s %s", ("peer", url), None)
    assert _PrivateRequestFilter().filter(record)
    assert record.getMessage() == "peer /api/v1/ws/chat"


def test_ws_limits_validation_and_storage_error(client, mock, monkeypatch):
    alice, headers = signup(client, 0)
    room = ChatRooms.create_companion_room("cpo_test01", UUID(alice))
    assert ChatRooms.create_companion_room("cpo_test01", UUID(alice)) == room
    with client.websocket_connect(connect_url(client, headers)) as ws:
        ws.send_text("bad json")
        assert ws.receive_json()["code"] == "VALIDATION_ERROR"
        assert send(ws, room, "msg-0001", "\x00")["code"] == "VALIDATION_ERROR"
        with monkeypatch.context() as failing:
            def store_error(*args):
                raise SQLAlchemyError("test write failure")

            failing.setattr(mock, "send", store_error)
            assert send(ws, room, "msg-0001", "실패") == {
                "type": "error", "code": "STORE_FAILED", "client_message_id": "msg-0001",
            }
        for i in range(5):
            ack = send(ws, room, f"msg-{i:04}", "성공")
            assert (ack["type"], ack["seq"]) == ("ack", i + 1)
        assert send(ws, room, "msg-0000", "재전송")["seq"] == 1
        assert send(ws, room, "msg-0005", "제한")["code"] == "RATE_LIMITED"
    assert len(client.get(f"{ROOMS}/{room}/messages", headers=headers).json()["items"]) == 5


def test_room_and_ticket_require_authentication(client, mock):
    assert client.post(f"{BASE}/ws-tickets", json={}).status_code == 401
    assert client.get(LIST).status_code == 401
    assert client.get(INBOX).status_code == 401
    with client.websocket_connect(f"{BASE}/ws/chat") as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    assert exc.value.code == 4401


def test_unknown_room_action_is_not_found(client, mock):
    _, headers = signup(client, 0)
    path = f"{ROOMS}/crm_FIXTURE/send"
    for authorization in ({}, headers):
        response = client.post(path, headers=authorization)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"
