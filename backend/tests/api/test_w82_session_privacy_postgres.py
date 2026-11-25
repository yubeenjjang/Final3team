"""W82 — 세션 종료·본인 정보 보존/삭제 검증 (실제 PostgreSQL).

기존 시험(test_auth_postgres·test_my_account_postgres·test_jobs_postgres)이 다루지 않는 부분만 확인한다.
- 로그아웃한 기기의 Access로 보호 API 호출 거부, 다른 기기는 유지
- 만료된 Access·만료된 Refresh 거부
- 정지(disabled) 계정의 보호 API·갱신 거부(401), 로그인 거부(403 ACCOUNT_DISABLED, A33)
- 열린 WebSocket이 로그아웃·탈퇴 뒤 종료(4403)
- 탈퇴자 메시지 본문은 방 보존 정책대로 남고, 작성자 이름은 다른 참여자에게 비공개
- 탈퇴 뒤 옛 이메일·비밀번호로 로그인 거부
"""
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.websockets import WebSocketDisconnect

from api.auth import state, tokens
from api.ingestion.db import create_ingestion_engine
from api.realtime import chat_socket
from shared.db import session as sessions

from .test_chat import ROOMS, connect_url, send, subscribe
from .test_my_account import AUTH, ME, PASSWORD, login, register_and_login

pytestmark = pytest.mark.db
PROFILE = f"{ME}/profile"


@pytest.fixture
def w82(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or os.environ["TEST_DB_URL"])
    service_engine = create_ingestion_engine(url)
    user_engine = create_async_engine(app_url.set(drivername="postgresql+psycopg"), hide_parameters=True)

    @event.listens_for(service_engine, "begin")
    def set_service_role(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    if not os.environ.get("TEST_DB_APP_URL"):
        @event.listens_for(user_engine.sync_engine, "begin")
        def set_app_role(connection):
            connection.exec_driver_sql("SET LOCAL ROLE noldaga_app")

    monkeypatch.setattr(sessions, "_service_engine", lambda: service_engine)
    monkeypatch.setattr(sessions, "_user_engine", lambda: user_engine)
    monkeypatch.setattr(state, "_auth_state", state.MemoryAuthState())
    monkeypatch.setattr(chat_socket, "tickets", chat_socket.MemoryTickets())
    monkeypatch.setattr(chat_socket, "bus", chat_socket.MemoryChatBus())
    monkeypatch.setattr(chat_socket, "limits", chat_socket.MessageLimits())
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MIN", "50")
    monkeypatch.setenv("JWT_SECRET", "fixture-postgresql-w82-signing-value-for-tests")
    for key in ("ACCESS_JWT_TTL_MIN", "REFRESH_TTL_DAYS", "REFRESH_LOCK_TTL_S"):
        monkeypatch.delenv(key, raising=False)

    uids: list[UUID] = []
    try:
        yield service_engine, uuid4().hex[:10], uids
    finally:
        client.portal.call(user_engine.dispose)
        params = {"uids": uids}
        try:
            with service_engine.begin() as db:
                rooms = db.scalars(text("""
                    SELECT room_id FROM public.chat_members WHERE user_id = ANY(CAST(:uids AS uuid[]))
                """), params).all()
                for table in ("chat_messages", "chat_members", "chat_rooms"):
                    db.execute(text(f"DELETE FROM public.{table} WHERE room_id = ANY(CAST(:rooms AS text[]))"),
                               {"rooms": list(rooms)})
                for table, columns in (("friendships", ("user_a", "user_b")),
                                       ("friend_requests", ("from_user", "to_user")),
                                       ("notifications", ("user_id",)), ("refresh_tokens", ("user_id",)),
                                       ("profiles", ("user_id",)), ("users", ("user_id",))):
                    where = " OR ".join(f"{column} = ANY(CAST(:uids AS uuid[]))" for column in columns)
                    db.execute(text(f"DELETE FROM public.{table} WHERE {where}"), params)
        finally:
            service_engine.dispose()


def _signup(client, uids, name):
    headers, user_id, refresh = register_and_login(client, name)
    uids.append(UUID(user_id))
    return headers, UUID(user_id), refresh


def _wait_for_close(ws, room):
    """서버 재확인 주기(RECHECK_SECONDS) 안에 구독 해지 알림 뒤 4403으로 닫혀야 한다."""
    reasons = []
    with pytest.raises(WebSocketDisconnect) as closed:
        for _ in range(20):
            frame = ws.receive_json()
            if frame.get("type") == "unsubscribed":
                reasons.append((frame["room_id"], frame["reason"]))
    assert closed.value.code == 4403
    assert reasons == [(room, "deleted")]


def test_w82_logout_expiry_and_disabled_accounts_end_sessions(client, w82):
    engine, key, uids = w82
    first, first_id, first_refresh = _signup(client, uids, "a" + key)
    credentials = {"email": f"a{key}@example.test", "password": PASSWORD}
    second_device, _, second_refresh = login(client, credentials)
    assert client.get(PROFILE, headers=first).status_code == 200

    # 로그아웃은 그 기기만: 같은 Access로 보호 API 거부, 다른 기기 Access·Refresh는 유지.
    logout = client.post(f"{AUTH}/logout", json={"refresh_token": first_refresh}, headers=first)
    assert logout.status_code == 204
    assert client.get(PROFILE, headers=first).status_code == 401
    assert client.post(f"{AUTH}/refresh", json={"refresh_token": first_refresh}).status_code == 401
    assert client.get(PROFILE, headers=second_device).status_code == 200

    # 만료된 Access(30분 수명이 지난 토큰)는 서명이 맞아도 거부.
    issued = datetime.now(timezone.utc) - timedelta(minutes=31)
    expired = {"Authorization": "Bearer " + tokens.issue_access_token(first_id, "user", issued, 1800)}
    assert client.get(PROFILE, headers=expired).status_code == 401

    # 만료 시각이 지난 Refresh는 교체되지 않음.
    with engine.begin() as db:
        db.execute(text("""
            UPDATE public.refresh_tokens SET expires_at = now() - interval '1 second' WHERE token_hash = :digest
        """), {"digest": tokens.refresh_hash(second_refresh)})
    assert client.post(f"{AUTH}/refresh", json={"refresh_token": second_refresh}).status_code == 401

    # 정지 계정: 남은 Access·Refresh와 로그인 모두 거부, 개인정보는 지우지 않음(탈퇴와 구분).
    other, other_id, other_refresh = _signup(client, uids, "b" + key)
    with engine.begin() as db:
        db.execute(text("UPDATE public.users SET status = 'disabled' WHERE user_id = :id"), {"id": other_id})
    assert client.get(PROFILE, headers=other).status_code == 401
    assert client.get(f"{ME}/favorites", headers=other).status_code == 401
    assert client.post(f"{AUTH}/refresh", json={"refresh_token": other_refresh}).status_code == 401
    blocked = client.post(f"{AUTH}/login", json={"email": f"b{key}@example.test", "password": PASSWORD})
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "ACCOUNT_DISABLED"
    with engine.connect() as db:
        assert db.scalar(text("SELECT display_name FROM public.profiles WHERE user_id = :id"),
                         {"id": other_id}) == "b" + key


def test_w82_websocket_closes_after_logout_and_withdrawal(client, w82):
    engine, key, uids = w82
    owner, owner_id, owner_refresh = _signup(client, uids, "o" + key)
    member, member_id, _ = _signup(client, uids, "m" + key)
    leaver, leaver_id, leaver_refresh = _signup(client, uids, "l" + key)
    with engine.begin() as db:
        for peer in (member_id, leaver_id):
            a, b = sorted((owner_id, peer))
            db.execute(text("INSERT INTO public.friendships (user_a, user_b) VALUES (:a, :b)"), {"a": a, "b": b})
    created = client.post(ROOMS, headers=owner, json={
        "type": "friend_group", "name": "W82", "invitee_ids": [str(member_id), str(leaver_id)],
    })
    assert created.status_code == 201
    room = created.json()["room_id"]
    for headers in (member, leaver):
        assert client.post(f"{ROOMS}/{room}/accept", headers=headers).status_code == 200

    # 로그아웃: 그 Access로 연 WebSocket이 다음 재확인 때 닫힘.
    with client.websocket_connect(connect_url(client, leaver)) as socket:
        subscribe(socket, room, 0)
        assert client.post(f"{AUTH}/logout", json={"refresh_token": leaver_refresh},
                           headers=leaver).status_code == 204
        _wait_for_close(socket, room)
    leaver, _, _ = login(client, {"email": f"l{key}@example.test", "password": PASSWORD})

    # 탈퇴: 방장의 열린 WebSocket이 닫히고, 메시지 본문은 남되 작성자 이름은 비공개.
    with client.websocket_connect(connect_url(client, owner)) as socket:
        subscribe(socket, room, 0)
        ack = send(socket, room, "msg-w82-1", "탈퇴 전 메시지")
        assert ack["type"] == "ack"
        assert client.request("DELETE", ME, headers=owner, json={"password": PASSWORD}).status_code == 204
        _wait_for_close(socket, room)

    history = client.get(f"{ROOMS}/{room}/messages", headers=member, params={"after_seq": 0})
    assert history.status_code == 200
    rows = [row for row in history.json()["items"] if row["message_id"] == ack["message_id"]]
    assert len(rows) == 1 and rows[0]["body"] == "탈퇴 전 메시지"
    assert rows[0]["sender_display_name"] is None
    assert client.patch(f"{ROOMS}/{room}", headers=member, json={"name": "승계"}).status_code == 200

    # 옛 이메일·비밀번호로 로그인 불가, 남은 Refresh도 갱신 불가.
    assert client.post(f"{AUTH}/login", json={
        "email": f"o{key}@example.test", "password": PASSWORD,
    }).status_code == 401
    assert client.post(f"{AUTH}/refresh", json={"refresh_token": owner_refresh}).status_code == 401
    with engine.connect() as db:
        assert db.scalar(text("SELECT count(*) FROM public.users WHERE email = :email"),
                         {"email": f"o{key}@example.test"}) == 0
