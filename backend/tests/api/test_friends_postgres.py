from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import Mock
from uuid import UUID

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError

from api.repositories import friends as repository
from api.services import friends as rules
from shared.db import session as sessions

from .test_friends import BLOCKS, FRIENDS, INBOX, act, assert_error, search, send
from .test_my_account import register_and_login
from .test_my_account_postgres import postgres_account

pytestmark = pytest.mark.db


@pytest.fixture
def friend_db(postgres_account, client, monkeypatch):
    engine, run, uids = postgres_account
    monkeypatch.setattr(rules, "search_limiter", rules.MemoryFriendSearchLimiter())
    members = []
    try:
        for suffix in ("a", "b", "c"):
            name = run + suffix
            headers, user_id, _ = register_and_login(client, name)
            uids.append(UUID(user_id))
            members.append((headers, user_id, name))
        yield engine, run, members
    finally:
        # API request IDs are generated at runtime and do not have the fixture prefix.
        with engine.begin() as db:
            ids = {"uids": uids}
            db.execute(text("""
                DELETE FROM public.friendships
                WHERE user_a = ANY(CAST(:uids AS uuid[])) OR user_b = ANY(CAST(:uids AS uuid[]))
            """), ids)
            db.execute(text("""
                DELETE FROM public.friend_requests
                WHERE from_user = ANY(CAST(:uids AS uuid[])) OR to_user = ANY(CAST(:uids AS uuid[]))
            """), ids)


def _concurrent(first, second):
    start = Barrier(2, timeout=5)

    def call(fn):
        start.wait()
        return fn()

    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs = [pool.submit(call, fn) for fn in (first, second)]
        return [job.result(timeout=15) for job in jobs]


def test_postgres_crossed_requests_and_rls(friend_db, client):
    engine, _, ((alice, alice_id, alice_name), (bob, bob_id, bob_name), (cara, cara_id, _)) = friend_db
    first, second = _concurrent(
        lambda: send(client, alice, bob_id),
        lambda: send(client, bob, alice_id),
    )
    assert {first.status_code, second.status_code} == {201}
    assert "X-Mock" not in first.headers and "X-Mock" not in second.headers
    assert {first.json()["status"], second.json()["status"]} == {"pending", "accepted"}
    request_id = first.json()["request_id"]
    assert second.json()["request_id"] == request_id
    assert search(client, alice, bob_name.upper()).json() == {"items": [{
        "user_id": bob_id, "display_name": bob_name, "friendship_status": "friends",
    }]}
    assert client.get(FRIENDS, headers=cara).json() == {"items": []}
    assert_error(act(client, cara, request_id, "accept"), 404, "NOT_FOUND")

    a, b = sorted((UUID(alice_id), UUID(bob_id)))
    with engine.begin() as db:
        assert db.execute(text("""
            SELECT user_a, user_b FROM public.friendships WHERE request_id = :id
        """), {"id": request_id}).one() == (a, b)
        assert db.execute(text("""
            SELECT status, responded_at FROM public.friend_requests
            WHERE least(from_user, to_user) = :a AND greatest(from_user, to_user) = :b
        """), {"a": a, "b": b}).one().status == "accepted"

    async def check_other_rows():
        async with sessions.user_db_session(UUID(cara_id)) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            for table in ("friendships", "friend_requests"):
                assert not await db.scalar(text(f"SELECT 1 FROM public.{table} WHERE request_id = :id"),
                                           {"id": request_id})

    client.portal.call(check_other_rows)
    assert client.put(f"{BLOCKS}/{bob_id}", headers=alice).json() == {"blocked": True}
    assert search(client, alice, bob_name).json() == {"items": []}
    assert search(client, bob, alice_name).json() == {"items": []}
    assert_error(send(client, bob, alice_id), 409, "BLOCKED")

    async def check_blocks():
        for uid, expected in ((alice_id, 1), (bob_id, 0), (cara_id, 0)):
            async with sessions.user_db_session(UUID(uid)) as db:
                assert await db.scalar(text("""
                    SELECT count(*) FROM public.user_blocks WHERE blocker = :alice AND blocked = :bob
                """), {"alice": UUID(alice_id), "bob": UUID(bob_id)}) == expected
        with pytest.raises(DBAPIError) as error:
            async with sessions.user_db_session(UUID(alice_id)) as db:
                await db.execute(text("DELETE FROM public.user_blocks WHERE blocker = public.app_current_user()"))
        assert error.value.orig.sqlstate == "42501"

    client.portal.call(check_blocks)


def test_postgres_accept_is_atomic_and_concurrent(friend_db, client):
    engine, _, ((alice, alice_id, alice_name), (bob, bob_id, bob_name), _) = friend_db
    request_id = send(client, alice, bob_id).json()["request_id"]
    assert search(client, alice, bob_name).json()["items"][0]["friendship_status"] == "pending_sent"
    assert search(client, bob, alice_name).json()["items"][0]["friendship_status"] == "pending_received"
    assert_error(act(client, alice, request_id, "reject"), 403, "FORBIDDEN")

    def fail_insert(_conn, _cursor, statement, _parameters, _context, _executemany):
        if "INSERT INTO public.friendships" in statement:
            raise RuntimeError("fixture rollback")

    event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        assert_error(act(client, bob, request_id, "accept"), 500, "INTERNAL_SERVER_ERROR")
    finally:
        event.remove(engine, "before_cursor_execute", fail_insert)
    row, = client.get(INBOX, headers=bob).json()["items"]
    assert row["request_id"] == request_id and row["user_id"] == alice_id and row["status"] == "pending"
    assert client.get(FRIENDS, headers=bob).json() == {"items": []}

    result = sorted(_concurrent(
        lambda: act(client, bob, request_id, "accept"),
        lambda: act(client, bob, request_id, "accept"),
    ), key=lambda response: response.status_code)
    assert result[0].status_code == 200
    assert result[0].json() == {"request_id": request_id, "status": "accepted"}
    assert_error(result[1], 409, "REQUEST_NOT_PENDING")
    assert client.get(FRIENDS, headers=bob).json()["items"][0]["user_id"] == alice_id
    for _ in range(2):
        assert client.delete(f"{FRIENDS}/{alice_id}", headers=bob).status_code == 204


def test_postgres_block_close_and_unblock_retention(friend_db, client, monkeypatch):
    engine, run, ((alice, alice_id, _), (bob, bob_id, _), _) = friend_db
    direct, group, companion, replacement = [f"crm_{run}{suffix}" for suffix in "dgcr"]
    pair_key = "|".join(sorted((alice_id, bob_id)))
    with engine.begin() as db:
        db.execute(text("""
            INSERT INTO public.chat_rooms (room_id, room_type, name, direct_key)
            VALUES (:direct, 'direct', NULL, :key), (:group, 'friend_group', '친구', NULL),
                   (:companion, 'companion', NULL, NULL)
        """), {"direct": direct, "group": group, "companion": companion, "key": pair_key})

    request_id = send(client, alice, bob_id).json()["request_id"]
    accepted, blocked = _concurrent(
        lambda: act(client, bob, request_id, "accept"),
        lambda: client.put(f"{BLOCKS}/{bob_id}", headers=alice),
    )
    assert accepted.status_code in (200, 409)
    if accepted.status_code == 409:
        assert_error(accepted, 409, "REQUEST_NOT_PENDING")
    assert blocked.json() == {"blocked": True}
    assert client.get(FRIENDS, headers=alice).json() == {"items": []}
    assert_error(send(client, alice, bob_id), 409, "BLOCKED")
    notify = Mock()
    monkeypatch.setattr(rules, "notify_chat_unblocked", notify)
    assert client.delete(f"{BLOCKS}/{alice_id}", headers=bob).status_code == 204
    notify.assert_not_called()
    assert client.delete(f"{BLOCKS}/{bob_id}", headers=alice).status_code == 204
    assert client.delete(f"{BLOCKS}/{bob_id}", headers=alice).status_code == 204
    notify.assert_called_once_with(UUID(alice_id), UUID(bob_id))
    assert client.get(FRIENDS, headers=bob).json() == {"items": []}
    assert send(client, alice, bob_id).json()["status"] == "pending"

    with engine.begin() as db:
        assert dict(db.execute(text("""
            SELECT room_id, status FROM public.chat_rooms WHERE room_id = ANY(CAST(:rooms AS text[]))
        """), {"rooms": [direct, group, companion]}).tuples().all()) == {
            direct: "closed", group: "active", companion: "active",
        }
        db.execute(text("""
            INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
            VALUES (:room, 'direct', :key)
        """), {"room": replacement, "key": pair_key})
        db.execute(text("""
            INSERT INTO public.friend_requests (request_id, from_user, to_user, status, responded_at)
            VALUES (:rejected, :alice, :bob, 'rejected', now() - interval '31 days'),
                   (:cancelled, :alice, :bob, 'cancelled', now() - interval '31 days')
        """), {"rejected": f"frq_{run}r", "cancelled": f"frq_{run}c",
                "alice": UUID(alice_id), "bob": UUID(bob_id)})

    items = client.get(INBOX, headers=bob).json()["items"]
    assert {item["status"] for item in items} == {"pending", "accepted" if accepted.status_code == 200 else "cancelled"}
    repository.purge_expired_requests()
    with engine.begin() as db:
        assert db.scalar(text("""
            SELECT count(*) FROM public.friend_requests WHERE request_id IN (:rejected, :cancelled)
        """), {"rejected": f"frq_{run}r", "cancelled": f"frq_{run}c"}) == 0
    assert client.get(INBOX, headers=bob).json()["items"] == items
