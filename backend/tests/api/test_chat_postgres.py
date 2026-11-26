import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state, tokens
from api.realtime import chat_socket
from api.repositories.chat import ChatRooms as PostgresChatRooms
from api.services.chat import ChatRooms
from shared.db import session as sessions

from .test_chat import INBOX, ROOMS, connect_url, send, subscribe

pytestmark = pytest.mark.db


@pytest.fixture
def database(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or os.environ["TEST_DB_URL"])
    service = create_engine(url, hide_parameters=True)
    app = create_async_engine(app_url.set(drivername="postgresql+psycopg"), hide_parameters=True)

    @event.listens_for(service, "begin")
    def assume_service(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    if not os.environ.get("TEST_DB_APP_URL"):
        @event.listens_for(app.sync_engine, "begin")
        def assume_app(connection):
            connection.exec_driver_sql("SET LOCAL ROLE noldaga_app")

    monkeypatch.setattr(sessions, "_service_engine", lambda: service)
    monkeypatch.setattr(sessions, "_user_engine", lambda: app)
    monkeypatch.setattr(state, "_auth_state", state.MemoryAuthState())
    monkeypatch.setattr(chat_socket, "tickets", chat_socket.MemoryTickets())
    monkeypatch.setattr(chat_socket, "bus", chat_socket.MemoryChatBus())
    monkeypatch.setattr(chat_socket, "limits", chat_socket.MessageLimits())
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("JWT_SECRET", "fixture-postgresql-chat-signing-value-for-tests")
    ids = [uuid4() for _ in range(4)]
    try:
        with service.begin() as db:
            for uid in ids:
                db.execute(text("""
                    INSERT INTO public.users (user_id, email, password_hash) VALUES (:uid, :email, 'fixture');
                """), {"uid": uid, "email": f"{uid}@example.test"})
                db.execute(text("""
                    INSERT INTO public.profiles (user_id, display_name) VALUES (:uid, :name)
                """), {"uid": uid, "name": uid.hex[:12]})
            for peer in ids[1:3]:
                a, b = sorted((ids[0], peer))
                db.execute(text("INSERT INTO public.friendships (user_a, user_b) VALUES (:a, :b)"), {"a": a, "b": b})
        auth = [
            {"Authorization": "Bearer " + tokens.issue_access_token(uid, "user", datetime.now(timezone.utc), 300)}
            for uid in ids
        ]
        yield service, ids, auth
    finally:
        client.portal.call(app.dispose)
        try:
            with service.begin() as db:
                params = {"uids": ids}
                rooms = """
                    SELECT room_id FROM public.chat_members WHERE user_id = ANY(CAST(:uids AS uuid[]))
                """
                db.execute(text(f"DELETE FROM public.chat_messages WHERE room_id IN ({rooms})"), params)
                room_ids = db.execute(text(rooms), params).scalars().all()
                db.execute(text("""
                    DELETE FROM public.chat_members WHERE room_id = ANY(CAST(:rooms AS text[]))
                """), {"rooms": room_ids})
                db.execute(text("""
                    DELETE FROM public.chat_rooms WHERE room_id = ANY(CAST(:rooms AS text[]))
                """), {"rooms": room_ids})
                for table, column in (("notifications", "user_id"), ("user_blocks", "blocker"),
                                      ("friendships", "user_a"), ("profiles", "user_id"), ("users", "user_id")):
                    extra = " OR user_b = ANY(CAST(:uids AS uuid[]))" if table == "friendships" else ""
                    db.execute(text(f"DELETE FROM public.{table} WHERE {column} = ANY(CAST(:uids AS uuid[])){extra}"), params)
        finally:
            service.dispose()


def test_postgres_group_invites_rls_and_ack(client, database):
    service, (alice, bob, carol, outsider), (a, b, c, d) = database
    response = client.post(ROOMS, headers=a, json={
        "type": "friend_group", "name": "친구들", "invitee_ids": [str(bob), str(carol)],
    })
    assert (response.status_code, response.headers.get("X-Mock")) == (201, None)
    room = response.json()["room_id"]
    path = f"{ROOMS}/{room}"

    async def visible(uid):
        async with sessions.user_db_session(uid) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            counts = (await db.execute(text("""
                SELECT (SELECT count(*) FROM public.chat_rooms WHERE room_id = :room),
                       (SELECT count(*) FROM public.chat_messages WHERE room_id = :room),
                       (SELECT count(*) FROM public.notifications WHERE ref_id = :room)
            """), {"room": room})).one()
            return tuple(counts)

    with client.websocket_connect(connect_url(client, a)) as owner:
        assert send(owner, room, "msg-db01", "입장 전")["seq"] == 1
        assert client.portal.call(visible, bob) == (1, 0, 1)
        assert client.portal.call(visible, outsider) == (0, 0, 0)
        assert client.get(f"{path}/messages", headers=d).status_code == 403
        assert client.post(f"{path}/accept", headers=b).status_code == 200
        with client.websocket_connect(connect_url(client, b)) as guest:
            subscribe(guest, room, 0)
            ack = send(owner, room, "msg-db02", "입장 후")
            with service.begin() as db:
                assert db.scalar(text("""
                    SELECT body FROM public.chat_messages WHERE message_id = :id
                """), {"id": ack["message_id"]}) == "입장 후"
            assert guest.receive_json()["seq"] == 2
        assert client.portal.call(visible, bob) == (1, 1, 1)
        assert client.post(f"{path}/read", headers=b, json={"seq": 9}).status_code == 204
        assert client.post(f"{path}/read", headers=b, json={"seq": 1}).status_code == 204
        rows = client.get(f"{path}/messages", headers=b, params={"after_seq": 0, "limit": 1}).json()["items"]
        assert [row["seq"] for row in rows] == [2]
        assert rows[0]["sender_display_name"] == alice.hex[:12]
        assert client.post(f"{path}/leave", headers=a).status_code == 200
        assert client.patch(path, headers=b, json={"name": "방장 승계"}).status_code == 200
    bob_id = client.get(INBOX, headers=b).json()["items"][0]["notification_id"]
    assert client.post(f"{INBOX}/read", headers=c, json={"ids": [bob_id]}).status_code == 204
    assert client.get(INBOX, headers=b).json()["unread_count"] == 1
    assert client.post(f"{INBOX}/read", headers=b, json={"ids": [bob_id]}).status_code == 204
    assert client.get(INBOX, headers=b).json()["unread_count"] == 0


def test_postgres_concurrent_direct_create_send_and_block(client, database):
    service, (alice, bob, _, _), (a, b, _, _) = database

    def create(pair):
        headers, friend = pair
        return client.post(ROOMS, headers=headers, json={"type": "direct", "friend_id": str(friend)})

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(create, [(a, bob), (b, alice)] * 3))
        assert sorted(r.status_code for r in results) == [200] * 5 + [201]
        room, = {r.json()["room_id"] for r in results}

        def write(index):
            return PostgresChatRooms.send(alice, room, f"concurrent-{index:02d}", "동시 전송", lambda *_: None)

        saves = list(pool.map(write, [0] * 5 + list(range(1, 10))))
        assert len({(message, seq) for message, seq, _ in saves[:5]}) == 1
        assert sorted(seq for _, seq, created in saves if created) == list(range(1, 11))

    with client.websocket_connect(connect_url(client, b)) as guest:
        subscribe(guest, room, 7)
        assert [guest.receive_json()["seq"] for _ in range(3)] == [8, 9, 10]
        with service.begin() as db:
            db.execute(text("INSERT INTO public.user_blocks (blocker, blocked) VALUES (:b, :a)"), {"a": alice, "b": bob})
        assert guest.receive_json()["status"] == "closed"
        assert guest.receive_json() == {"type": "unsubscribed", "room_id": room, "reason": "blocked"}
        assert create((a, bob)).json()["error"]["code"] == "BLOCKED"
        assert send(guest, room, "after-block", "차단 후")["code"] == "FORBIDDEN"

    with service.begin() as db:
        db.execute(text("DELETE FROM public.user_blocks WHERE blocker = :b AND blocked = :a"), {"a": alice, "b": bob})
    ChatRooms.close_direct_room_on_unblock(alice, bob)
    assert client.get(f"{ROOMS}/{room}/messages", headers=a).status_code == 403
    new_room = create((a, bob))
    assert new_room.status_code == 201 and new_room.json()["room_id"] != room
    ChatRooms.close_direct_room_on_unblock(alice, bob)
    assert create((a, bob)).json()["room_id"] == new_room.json()["room_id"]


def test_postgres_direct_room_list_shows_peer_only_to_members(client, database):
    _, (alice, bob, _, _), (a, b, _, outsider) = database
    response = client.post(ROOMS, headers=a, json={"type": "direct", "friend_id": str(bob)})
    assert response.status_code == 201
    room = response.json()["room_id"]
    for headers, peer in ((a, bob), (b, alice)):
        response = client.get("/api/v1/me/chat-rooms", headers=headers)
        assert response.status_code == 200
        assert response.json()["items"] == [{
            "room_id": room, "room_type": "direct", "name": None, "status": "active",
            "last_message_at": None, "unread_count": 0, "my_status": "joined",
            "peer_display_name": peer.hex[:12], "festival_name": None, "meet_at": None,
        }]
    assert client.get("/api/v1/me/chat-rooms", headers=outsider).json()["items"] == []


def test_postgres_companion_helpers_share_transaction(client, database):
    _, (owner, member, _, _), (owner_auth, member_auth, _, _) = database
    post_id = f"cpo_{uuid4().hex[:20]}"
    with sessions.service_db_session() as db:
        room = ChatRooms.create_companion_room(post_id, owner, db=db)
        assert ChatRooms.create_companion_room(post_id, owner, db=db) == room
    with client.websocket_connect(connect_url(client, owner_auth)) as host:
        assert send(host, room, "msg-before", "승인 전")["seq"] == 1
        with sessions.service_db_session() as db:
            ChatRooms.add_member(room, member, db=db)
            ChatRooms.add_member(room, member, db=db)
        assert send(host, room, "msg-after", "승인 후")["seq"] == 2
    assert client.post(f"{ROOMS}/{room}/leave", headers=member_auth).status_code == 403
    assert [row["seq"] for row in client.get(f"{ROOMS}/{room}/messages", headers=member_auth).json()["items"]] == [2]
