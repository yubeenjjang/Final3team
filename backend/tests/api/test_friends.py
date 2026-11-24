from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from api.services import friends, mock_friends

from .test_my_account import ME, PASSWORD, register_and_login

SEARCH = "/api/v1/users/search"
REQUESTS = "/api/v1/friend-requests"
INBOX = f"{ME}/friend-requests"
FRIENDS = f"{ME}/friends"
BLOCKS = f"{ME}/blocks"


@pytest.fixture(autouse=True)
def friend_state(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    monkeypatch.setattr(mock_friends, "store", mock_friends.MockFriends())
    monkeypatch.setattr(friends, "search_limiter", friends.MemoryFriendSearchLimiter())


def send(client, headers, user_id):
    return client.post(REQUESTS, headers=headers, json={"to_user_id": user_id})


def search(client, headers, nickname):
    return client.get(SEARCH, headers=headers, params={"nickname": nickname})


def act(client, headers, request_id, action):
    return client.post(f"{REQUESTS}/{request_id}/{action}", headers=headers)


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("mode", ["mock", "db"])
def test_friend_endpoints_require_authentication(client, monkeypatch, mode):
    monkeypatch.setenv("AUTH_PROVIDER", mode)
    other = str(uuid4())
    for method, path, options in (
        ("GET", SEARCH, {"params": {"nickname": "Another"}}),
        ("POST", REQUESTS, {"json": {"to_user_id": other}}),
        ("GET", INBOX, {}),
        ("POST", f"{REQUESTS}/frq_000001/accept", {}),
        ("GET", FRIENDS, {}),
        ("DELETE", f"{FRIENDS}/{other}", {}),
        ("PUT", f"{BLOCKS}/{other}", {}),
        ("DELETE", f"{BLOCKS}/{other}", {}),
    ):
        response = client.request(method, path, **options)
        assert_error(response, 401, "UNAUTHORIZED")
        assert ("X-Mock" in response.headers) is (mode == "mock")


def test_mock_exact_search_and_crossed_request(client):
    alice, alice_id, _ = register_and_login(client, "Alice")
    bob, bob_id, _ = register_and_login(client, "Bob")
    cara, _, _ = register_and_login(client, "Cara")

    for value in ("Bo", "Bob ", "Alice", "Bob@exam"):
        assert search(client, alice, value).json() == {"items": []}
    assert search(client, alice, "bOB").json() == {"items": [{
        "user_id": bob_id, "display_name": "Bob", "friendship_status": "none",
    }]}
    assert_error(send(client, alice, alice_id), 404, "NOT_FOUND")
    assert_error(send(client, alice, str(uuid4())), 404, "NOT_FOUND")

    first = send(client, alice, bob_id)
    request_id = first.json()["request_id"]
    assert first.status_code == 201 and first.json()["status"] == "pending"
    assert search(client, alice, "Bob").json()["items"][0]["friendship_status"] == "pending_sent"
    assert search(client, bob, "Alice").json()["items"][0]["friendship_status"] == "pending_received"
    assert_error(send(client, alice, bob_id), 409, "REQUEST_PENDING")

    received = client.get(INBOX, headers=bob).json()["items"]
    assert len(received) == 1
    assert received[0] == {
        "request_id": request_id, "user_id": alice_id, "display_name": "Alice",
        "status": "pending", "created_at": received[0]["created_at"],
    }
    sent = client.get(INBOX, headers=alice, params={"box": "sent"}).json()["items"]
    assert sent == [{**received[0], "user_id": bob_id, "display_name": "Bob"}]
    assert client.get(INBOX, headers=cara).json() == {"items": []}
    assert_error(act(client, cara, request_id, "accept"), 404, "NOT_FOUND")
    assert_error(act(client, alice, request_id, "accept"), 403, "FORBIDDEN")
    assert_error(act(client, bob, request_id, "cancel"), 403, "FORBIDDEN")

    crossed = send(client, bob, alice_id)
    assert crossed.status_code == 201
    assert crossed.json() == {"request_id": request_id, "status": "accepted"}
    assert_error(send(client, alice, bob_id), 409, "ALREADY_FRIENDS")
    assert_error(act(client, bob, request_id, "accept"), 409, "REQUEST_NOT_PENDING")
    assert search(client, alice, "Bob").json()["items"][0]["friendship_status"] == "friends"
    for headers, other, name in ((alice, bob_id, "Bob"), (bob, alice_id, "Alice")):
        items = client.get(FRIENDS, headers=headers).json()["items"]
        assert len(items) == 1
        assert items[0] == {"user_id": other, "display_name": name, "since": items[0]["since"]}
        assert datetime.fromisoformat(items[0]["since"]).tzinfo
    assert client.get(FRIENDS, headers=alice, params={"page": 2}).json() == {"items": []}
    assert client.get(FRIENDS, headers=cara).json() == {"items": []}
    for _ in range(2):
        deleted = client.delete(f"{FRIENDS}/{bob_id}", headers=alice)
        assert deleted.status_code == 204 and deleted.content == b""
    assert client.get(FRIENDS, headers=bob).json() == {"items": []}


def test_mock_explicit_actions_and_bidirectional_block(client, monkeypatch):
    alice, alice_id, _ = register_and_login(client, "Alice")
    bob, bob_id, _ = register_and_login(client, "Bob")
    notify = Mock()
    monkeypatch.setattr(friends, "notify_chat_unblocked", notify)

    for action, actor, status in (("reject", bob, "rejected"), ("cancel", alice, "cancelled"),
                                  ("accept", bob, "accepted")):
        request_id = send(client, alice, bob_id).json()["request_id"]
        response = act(client, actor, request_id, action)
        assert response.status_code == 200
        assert response.json() == {"request_id": request_id, "status": status}

    assert client.put(f"{BLOCKS}/{bob_id}", headers=alice).json() == {"blocked": True}
    assert client.get(FRIENDS, headers=bob).json() == {"items": []}
    assert client.delete(f"{BLOCKS}/{alice_id}", headers=bob).status_code == 204
    notify.assert_not_called()
    for headers, other, name in ((alice, bob_id, "Bob"), (bob, alice_id, "Alice")):
        assert search(client, headers, name).json() == {"items": []}
        assert_error(send(client, headers, other), 409, "BLOCKED")

    # A reciprocal block remains in force after one side deletes its own row.
    assert client.put(f"{BLOCKS}/{alice_id}", headers=bob).status_code == 200
    for _ in range(2):
        response = client.delete(f"{BLOCKS}/{bob_id}", headers=alice)
        assert response.status_code == 204 and response.content == b""
    notify.assert_called_once_with(UUID(alice_id), UUID(bob_id))
    assert search(client, alice, "Bob").json() == {"items": []}
    assert client.delete(f"{BLOCKS}/{alice_id}", headers=bob).status_code == 204
    assert search(client, alice, "Bob").json()["items"][0]["friendship_status"] == "none"

    pending_id = send(client, alice, bob_id).json()["request_id"]
    assert client.put(f"{BLOCKS}/{alice_id}", headers=bob).status_code == 200
    assert client.get(INBOX, headers=bob).json()["items"][0]["status"] == "cancelled"
    assert_error(act(client, bob, pending_id, "accept"), 409, "REQUEST_NOT_PENDING")


def test_search_limit_is_per_user_and_expires(client, monkeypatch):
    alice, _, _ = register_and_login(client, "Alice")
    bob, _, _ = register_and_login(client, "Bob")
    now = 100.0
    monkeypatch.setattr(friends, "monotonic", lambda: now)

    for _ in range(20):
        assert search(client, alice, "Bob").status_code == 200
    limited = search(client, alice, "Bob")
    assert_error(limited, 429, "RATE_LIMITED")
    assert limited.headers["Retry-After"] == "60" and limited.json()["error"]["retryable"]
    assert search(client, bob, "Alice").status_code == 200
    now += 59.25
    assert search(client, alice, "Bob").headers["Retry-After"] == "1"
    now += 0.75
    assert search(client, alice, "Bob").status_code == 200


def test_mock_validation_retention_and_account_deletion(client):
    alice, alice_id, _ = register_and_login(client, "Alice")
    bob, bob_id, _ = register_and_login(client, "Bob")
    assert_error(client.put(f"{BLOCKS}/{alice_id}", headers=alice), 422, "VALIDATION_ERROR")
    assert_error(send(client, alice, "invalid"), 422, "VALIDATION_ERROR")
    assert_error(search(client, alice, "x"), 422, "VALIDATION_ERROR")
    assert_error(search(client, alice, "x" * 13), 422, "VALIDATION_ERROR")
    assert_error(client.get(INBOX, headers=alice, params={"box": "other"}), 422, "VALIDATION_ERROR")
    assert_error(client.get(FRIENDS, headers=alice, params={"page": 0}), 422, "VALIDATION_ERROR")
    assert_error(act(client, alice, "bad", "cancel"), 422, "VALIDATION_ERROR")
    assert_error(act(client, alice, "frq_000001", "other"), 422, "VALIDATION_ERROR")

    rejected = send(client, alice, bob_id).json()["request_id"]
    assert act(client, bob, rejected, "reject").status_code == 200
    mock_friends.store.requests[rejected].responded_at = datetime.now(timezone.utc) - timedelta(days=30)
    assert client.get(INBOX, headers=bob).json() == {"items": []}
    assert_error(act(client, bob, rejected, "reject"), 404, "NOT_FOUND")
    pending = send(client, alice, bob_id).json()["request_id"]
    mock_friends.store.requests[pending].created_at -= timedelta(days=60)
    assert client.get(INBOX, headers=bob).json()["items"][0]["request_id"] == pending
    assert act(client, bob, pending, "accept").status_code == 200
    assert client.request("DELETE", ME, headers=alice, json={"password": PASSWORD}).status_code == 204
    assert client.get(FRIENDS, headers=bob).json() == {"items": []}
    assert client.get(INBOX, headers=bob).json() == {"items": []}
