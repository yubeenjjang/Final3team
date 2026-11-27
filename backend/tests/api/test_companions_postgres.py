from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event
from time import monotonic, sleep
from uuid import UUID

import pytest
from sqlalchemy import text

from api.errors import ApiError
from api.repositories.companions import CompanionWrites, maintain_companions
from api.services.companion_rules import KST, now_utc
from shared.db import session as sessions

from .test_companions import APPLICATIONS, POSTS, assert_error, post_body
from .test_my_account import register_and_login
from .test_my_account_postgres import postgres_account  # noqa: F401

pytestmark = pytest.mark.db


@pytest.fixture
def companion_sample(client, postgres_account):
    engine, key, uids = postgres_account
    people = [register_and_login(client, prefix + key) for prefix in ("a", "b", "c")]
    uids.extend(UUID(person[1]) for person in people)
    festival_id = "fst_" + key
    future = now_utc() + timedelta(days=1)
    params = {"festival_id": festival_id, "day": future.astimezone(KST).date(), "rooms": []}
    with engine.begin() as db:
        db.execute(text("""
            INSERT INTO public.festivals (festival_id, title, category, region_code, source_class_level2,
                                          review_status, published_at, start_date, end_date)
            VALUES (:festival_id, '시험 축제', 'festival', 'SEOUL', 'EV01', 'approved', now(), :day, :day)
        """), params)
    try:
        response = client.post(POSTS, headers=people[0][0], json=post_body(
            festival_id=festival_id, meet_at=future.isoformat(),
        ))
        assert response.status_code == 201 and "X-Mock" not in response.headers
        result = response.json()
        yield engine, people, result
    finally:
        with engine.begin() as db:
            params["rooms"] = db.scalars(text("""
                SELECT room_id FROM public.companion_posts WHERE festival_id = :festival_id
            """), params).all()
            for table in ("meeting_places", "companion_applications"):
                db.execute(text(f"""
                    DELETE FROM public.{table} WHERE post_id IN (
                        SELECT post_id FROM public.companion_posts WHERE festival_id = :festival_id
                    )
                """), params)
            db.execute(text("DELETE FROM public.companion_posts WHERE festival_id = :festival_id"), params)
            for table in ("chat_messages", "chat_members", "chat_rooms"):
                db.execute(text(f"DELETE FROM public.{table} WHERE room_id = ANY(CAST(:rooms AS text[]))"), params)


def test_db_companions_rls_and_competing_approvals(client, companion_sample):
    engine, people, result = companion_sample
    (owner, owner_raw_id, _), (first, first_raw_id, _), (second, second_raw_id, _) = people
    detail = f"{POSTS}/{result['post_id']}"
    applications = detail + "/applications"
    place = detail + "/meeting-place"
    public_detail = client.get(detail).json()
    assert public_detail["my_application_status"] is None
    assert public_detail["room_id"] is None
    assert client.get(detail, headers=owner).json()["room_id"] == result["room_id"]
    assert client.get(detail, headers=first).json()["room_id"] is None
    assert client.put(place, headers=owner, json={"name": "정문", "lat": 37.5, "lng": 127}).status_code == 200

    requested = []
    for headers in (first, second):
        response = client.post(applications, headers=headers, json={"message": "같이 갈래요"})
        assert response.status_code == 201
        requested.append(response.json()["application_id"])
    assert_error(client.post(applications, headers=first), 409, "APPLICATION_EXISTS")
    first_app, second_app = requested
    params = {**result, "first_app": first_app, "second_app": second_app}

    async def read_rls(raw_id):
        async with sessions.user_db_session(UUID(raw_id)) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            own_app = await db.scalars(text("""
                SELECT application_id FROM public.companion_applications WHERE post_id = :post_id
                ORDER BY application_id
            """), params)
            counts = {}
            for table in ("chat_rooms", "chat_members", "chat_messages", "meeting_places"):
                column = "post_id" if table == "meeting_places" else "room_id"
                counts[table] = await db.scalar(text(
                    f"SELECT count(*) FROM public.{table} WHERE {column} = :{column}"
                ), params)
            return list(own_app), counts

    hidden = {"chat_rooms": 0, "chat_members": 0, "chat_messages": 0, "meeting_places": 0}
    assert client.portal.call(read_rls, first_raw_id) == ([first_app], hidden)
    assert client.portal.call(read_rls, second_raw_id) == ([second_app], hidden)
    assert_error(client.get(place, headers=first), 403, "FORBIDDEN")
    assert_error(client.get(applications, headers=second), 403, "FORBIDDEN")
    incoming = client.get(applications, headers=owner, params={"status": "pending"}).json()["items"]
    assert {row["application_id"] for row in incoming} == set(requested)
    assert all(row["applicant_age"] == now_utc().astimezone(KST).year - 2000 for row in incoming)

    first_written, second_connected, release_first = Event(), Event(), Event()
    pids = {}

    def approve_first():
        with sessions.service_db_session() as db:
            pids["first"] = db.scalar(text("SELECT pg_backend_pid()"))
            approved = CompanionWrites(db, UUID(owner_raw_id)).decide_application(first_app, "approve")
            first_written.set()
            assert release_first.wait(15)
        return approved

    def approve_second():
        assert first_written.wait(15)
        try:
            with sessions.service_db_session() as db:
                pids["second"] = db.scalar(text("SELECT pg_backend_pid()"))
                second_connected.set()
                CompanionWrites(db, UUID(owner_raw_id)).decide_application(second_app, "approve")
        except ApiError as error:
            return error
        pytest.fail("두 번째 신청까지 승인됐습니다.")

    with ThreadPoolExecutor(max_workers=2) as pool:
        winner = pool.submit(approve_first)
        loser = pool.submit(approve_second)
        try:
            assert second_connected.wait(15)
            assert pids["first"] != pids["second"]
            deadline = monotonic() + 5
            with engine.connect() as db:
                while pids["first"] not in db.scalar(text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["second"]}):
                    assert monotonic() < deadline and not loser.done(), "두 번째 연결이 행 잠금을 기다리지 않았습니다."
                    sleep(0.01)
            assert client.portal.call(read_rls, first_raw_id) == ([first_app], hidden)
        finally:
            release_first.set()
        assert winner.result(timeout=15).post_status == "full"
        error = loser.result(timeout=15)
        assert (error.status, error.code) == (409, "CAPACITY_FULL")

    assert client.portal.call(read_rls, first_raw_id) == (
        [first_app], {"chat_rooms": 1, "chat_members": 2, "chat_messages": 1, "meeting_places": 1},
    )
    assert client.portal.call(read_rls, second_raw_id) == ([second_app], hidden)
    assert client.get(place, headers=first).json()["lat"] == 37.5
    assert_error(client.post(f"{APPLICATIONS}/{first_app}/cancel", headers=first), 409, "APPLICATION_NOT_PENDING")
    assert client.get(detail).json()["approved_count"] == 1
    first_detail = client.get(detail, headers=first).json()
    assert first_detail["my_application_status"] == "approved"
    assert first_detail["room_id"] == result["room_id"]
    second_detail = client.get(detail, headers=second).json()
    assert second_detail["my_application_status"] == "pending"
    assert second_detail["room_id"] is None
    assert client.post(detail + "/end", headers=owner).json()["status"] == "ended"
    assert client.get(detail, headers=first).json()["room_id"] == result["room_id"]
    assert client.get(place, headers=first).json()["name"] == "정문"

    with engine.begin() as db:
        room = db.execute(text("""
            SELECT status, read_only_at, last_seq FROM public.chat_rooms WHERE room_id = :room_id
        """), params).one()
        assert room.status == "read_only" and room.last_seq == 2
        assert db.scalar(text("""
            SELECT count(*) FROM public.notifications
            WHERE ref_id IN (:first_app, :second_app) AND type = 'companion_approved'
        """), params) == 1
        maintain_companions(db, room.read_only_at + timedelta(hours=72) - timedelta(microseconds=1))
        assert db.scalar(text("SELECT memo FROM public.companion_posts WHERE post_id = :post_id"), params)
        maintain_companions(db, room.read_only_at + timedelta(hours=72))
        assert db.execute(text("""
            SELECT memo, status, approved_count FROM public.companion_posts WHERE post_id = :post_id
        """), params).one() == (None, "ended", 1)
        assert db.scalar(text("""
            SELECT count(*) FROM public.chat_messages
            WHERE room_id = :room_id AND body IS NULL AND deleted_at IS NOT NULL
        """), params) == 2
        assert db.scalar(text("""
            SELECT count(*) FROM public.companion_applications WHERE post_id = :post_id AND message IS NOT NULL
        """), params) == 0
    assert client.get(place, headers=first).json() == {"status": "undecided"}


def test_db_companion_room_list_respects_post_and_festival_publication(client, companion_sample):
    engine, ((owner, owner_id, _), (member, _, _), _), created = companion_sample
    detail = f"{POSTS}/{created['post_id']}"
    app_id = client.post(f"{detail}/applications", headers=member).json()["application_id"]
    assert client.post(f"{APPLICATIONS}/{app_id}/approve", headers=owner).status_code == 200
    path = "/api/v1/me/chat-rooms?filter=companion"
    meeting = datetime.fromisoformat(client.get(detail, headers=owner).json()["meet_at"])
    room, = client.get(path, headers=member).json()["items"]
    assert datetime.fromisoformat(room["meet_at"]) == meeting
    # 승인 시 동행방에 안내 메시지가 하나 생기므로 last_message_at·unread_count는 값만 확인한다.
    assert room["last_message_at"] is not None and room["unread_count"] >= 0
    assert {key: value for key, value in room.items() if key not in ("last_message_at", "unread_count")} == {
        "room_id": created["room_id"], "room_type": "companion", "name": None, "status": "active",
        "my_status": "joined",
        "peer_display_name": None, "festival_name": "시험 축제", "meet_at": room["meet_at"],
    }

    with engine.begin() as db:
        db.execute(text("""
            UPDATE public.festivals SET review_status = 'hidden'
            WHERE festival_id = (SELECT festival_id FROM public.companion_posts WHERE post_id = :post_id)
        """), created)
    unpublished = {**room, "festival_name": None}
    assert client.get(path, headers=member).json()["items"] == [unpublished]

    with engine.begin() as db:
        db.execute(text("""
            UPDATE public.companion_posts SET hidden_at = now(), hidden_by = :owner_id WHERE post_id = :post_id
        """), {**created, "owner_id": owner_id})
    assert client.get(path, headers=member).json()["items"] == [{**unpublished, "meet_at": None}]
    assert client.get(path, headers=owner).json()["items"] == [unpublished]


def test_db_manual_close_and_automatic_end(client, companion_sample):
    engine, people, result = companion_sample
    owner, _, _ = people[0]
    detail = f"{POSTS}/{result['post_id']}"
    assert client.patch(detail, json={"capacity": 2}, headers=owner).json()["status"] == "open"
    assert client.post(detail + "/close", headers=owner).json()["status"] == "full"
    assert client.patch(detail, json={"capacity": 3}, headers=owner).json()["status"] == "full"
    with engine.begin() as db:
        meet_at = db.scalar(text("""
            UPDATE public.companion_posts SET status = 'open' WHERE post_id = :post_id RETURNING meet_at
        """), result)
        assert db.scalar(text("SELECT status FROM public.companion_posts WHERE post_id = :post_id"), result) == "full"
        cutoff = meet_at + timedelta(hours=12)
        maintain_companions(db, cutoff)
        assert db.execute(text("""
            SELECT p.status, p.ended_at, r.read_only_at FROM public.companion_posts p
            JOIN public.chat_rooms r USING (room_id) WHERE p.post_id = :post_id
        """), result).one() == ("ended", cutoff, cutoff)


def test_db_companion_apply_and_approval_check_blocks(client, companion_sample):
    engine, people, result = companion_sample
    (owner, owner_id, _), (first, first_id, _), (second, second_id, _) = people
    applications = f"{POSTS}/{result['post_id']}/applications"
    pending = client.post(applications, headers=first).json()["application_id"]

    assert client.put(f"/api/v1/me/blocks/{owner_id}", headers=first).status_code == 200
    assert client.put(f"/api/v1/me/blocks/{second_id}", headers=owner).status_code == 200
    assert_error(client.post(applications, headers=second), 409, "BLOCKED")
    assert_error(client.post(f"{APPLICATIONS}/{pending}/approve", headers=owner), 409, "BLOCKED")
    with engine.begin() as db:
        assert db.scalar(text("""
            SELECT approved_count FROM public.companion_posts WHERE post_id = :post_id
        """), result) == 0
        assert db.scalars(text("""
            SELECT application_id FROM public.companion_applications
            WHERE post_id = :post_id AND status = 'pending'
        """), result).all() == [pending]
        assert db.scalar(text("""
            SELECT count(*) FROM public.chat_members WHERE room_id = :room_id AND status = 'joined'
        """), result) == 1
