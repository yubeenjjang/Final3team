from contextlib import contextmanager

import pytest
from sqlalchemy import event, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from api.repositories import reports as repository
from api.repositories.chat import ChatRooms
from shared.db import session as sessions

from .test_chat import INBOX, ROOMS
from .test_chat_postgres import database
from .test_friends_postgres import _concurrent
from .test_notify import ADMIN, REPORTS, decide, submit

pytestmark = pytest.mark.db


def test_postgres_report_scope_concurrency_rls_and_audit(client, database, monkeypatch):
    engine, (owner, reporter, invitee, operator), (a, b, c, reviewer) = database
    assert client.post(REPORTS, json={"target_type": "user", "target_id": str(owner), "reason": "abuse"}).status_code == 401
    with engine.begin() as db:
        db.execute(text("UPDATE public.profiles SET role = 'operator' WHERE user_id = :id"), {"id": operator})
    room = client.post(ROOMS, headers=a, json={
        "type": "friend_group", "name": "DB 신고 시험", "invitee_ids": [str(reporter), str(invitee)],
    }).json()["room_id"]
    assert submit(client, b, "chat_room", room).status_code == 404
    assert submit(client, reviewer, "chat_room", room).status_code == 404
    before, _, _ = ChatRooms.send(owner, room, "report-db-0", "입장 전", lambda *_: None)
    assert client.post(f"{ROOMS}/{room}/accept", headers=b).status_code == 200
    message_id, _, _ = ChatRooms.send(owner, room, "report-db-1", "신고 메시지", lambda *_: None)
    ChatRooms.send(owner, room, "report-db-2", "같은 방의 다른 메시지", lambda *_: None)
    with engine.begin() as db:
        db.execute(text("""
            INSERT INTO public.notifications (user_id, type, ref_type, ref_id, created_at)
            VALUES (:uid, 'room_invited', 'chat_room', :room, statement_timestamp() - interval '90 days')
        """), {"uid": reporter, "room": room})
    try:
        assert client.get(INBOX, headers=b).json()["unread_count"] == 1
        assert submit(client, b, "chat_message", before).status_code == 404
        assert submit(client, c, "chat_message", message_id).status_code == 404
        first, second = _concurrent(
            lambda: submit(client, b, "chat_message", message_id),
            lambda: submit(client, b, "chat_message", f"0{message_id}"),
        )
        assert sorted(response.status_code for response in (first, second)) == [201, 409]
        created = first if first.status_code == 201 else second
        assert "X-Mock" not in created.headers
        message_report = created.json()["report_id"]
        room_report = submit(client, b, "chat_room", room).json()["report_id"]

        async def visible_ids(actor):
            async with sessions.user_db_session(actor) as db:
                assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
                assert not await db.scalar(text("SELECT has_table_privilege('public.chat_admin_access', 'SELECT')"))
                return set((await db.scalars(text("SELECT report_id FROM public.reports"))).all())

        assert client.portal.call(visible_ids, reporter) == {message_report, room_report}
        assert client.portal.call(visible_ids, owner) == set()
        assert client.get(ADMIN, headers=b, params={"report_id": message_report}).status_code == 403
        page = client.get(ADMIN, headers=reviewer, params={"status": "received"})
        assert "X-Mock" not in page.headers
        assert {room_report, message_report} <= {row["report_id"] for row in page.json()["items"]}

        # Keep append-only audit rows in an outer transaction so fixture cleanup can roll back.
        with engine.connect() as connection:
            outer = connection.begin()

            @contextmanager
            def in_test_transaction():
                with Session(bind=connection, join_transaction_mode="create_savepoint") as db, db.begin():
                    yield db

            monkeypatch.setattr(repository, "service_db_session", in_test_transaction)
            trace = []

            def record_order(_conn, _cursor, statement, _parameters, _context, _executemany):
                if "INSERT INTO public.chat_admin_access" in statement:
                    trace.append("audit")
                if "THEN m.body" in statement:
                    trace.append("message")

            event.listen(connection, "before_cursor_execute", record_order)
            room_view = client.get(ADMIN, headers=reviewer, params={"report_id": room_report}).json()
            assert room_view["message"] is None
            assert room_view["room"]["room_id"] == room
            assert room_view["report"]["status"] == "reviewing"
            views = [client.get(ADMIN, headers=reviewer, params={"report_id": message_report}).json() for _ in range(2)]
            assert trace == ["audit", "audit", "message", "audit", "message"]
            for view in views:
                assert view["message"]["message_id"] == message_id
                assert view["message"]["body"] == "신고 메시지"
            assert room_view["access_id"] < views[0]["access_id"] < views[1]["access_id"]
            access = connection.execute(text("""
                SELECT admin_id, room_id, report_id, reason FROM public.chat_admin_access
                WHERE report_id IN (:msg, :room_report) ORDER BY access_id
            """), {"msg": message_report, "room_report": room_report}).all()
            assert access == [(operator, room, rpt, "abuse") for rpt in (room_report, message_report, message_report)]
            with pytest.raises(DBAPIError, match="permission denied"), connection.begin_nested():
                connection.execute(text("DELETE FROM public.chat_admin_access WHERE report_id = :id"), {"id": message_report})
            result = decide(client, reviewer, message_report, "hide_message").json()
            assert result["handled_by"] == str(operator) and result["status"] == "actioned"
            assert connection.execute(text("""
                SELECT action, note FROM public.report_moderation WHERE report_id = :id
            """), {"id": message_report}).one() == ("hide_message", "검토 완료")
            assert connection.scalar(text("""
                SELECT deleted_at IS NOT NULL FROM public.chat_messages WHERE message_id = :id
            """), {"id": message_id})
            assert decide(client, reviewer, room_report, "close_room").json()["status"] == "actioned"
            outer.rollback()
    finally:
        with engine.begin() as db:
            db.execute(text("DELETE FROM public.reports WHERE reporter_id = :uid"), {"uid": reporter})
