import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state, tokens
from api.ingestion.db import create_ingestion_engine
from api.services import account_deletion
from shared.db import session as sessions

from .test_my_account import AUTH, ME, PASSWORD, login, register_and_login

pytestmark = pytest.mark.db


@pytest.fixture
def postgres_account(client, monkeypatch):
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
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("AUTH_RATE_LIMIT_PER_MIN", "20")
    monkeypatch.setenv("JWT_SECRET", "fixture-postgresql-account-signing-value")

    run = uuid4().hex[:10]
    uids = []
    fixture = {"prefix": run + "%", "uids": uids}
    try:
        yield service_engine, run, uids
    finally:
        client.portal.call(user_engine.dispose)
        try:
            with service_engine.begin() as db:
                for table, column in (("friendships", "user_a"), ("user_blocks", "blocker"),
                                      ("favorites", "user_id")):
                    db.execute(text(f"DELETE FROM public.{table} WHERE {column} = ANY(CAST(:uids AS uuid[]))"),
                               fixture)
                for table, column in (
                    ("assistant_runs", "run_id"), ("chat_members", "room_id"),
                    ("companion_applications", "application_id"), ("companion_posts", "post_id"),
                    ("chat_rooms", "room_id"), ("friend_requests", "request_id"),
                    ("festivals", "festival_id"),
                ):
                    db.execute(text(f"DELETE FROM public.{table} WHERE substring({column} FROM 5) LIKE :prefix"),
                               fixture)
                for table in ("user_festival_preferences", "notifications", "refresh_tokens", "profiles", "users"):
                    db.execute(text(f"DELETE FROM public.{table} WHERE user_id = ANY(CAST(:uids AS uuid[]))"), fixture)
        finally:
            service_engine.dispose()


def _seed_account_data(db, first, second, ids):
    for key, review, category, start in (
        ("festival", "approved", "festival", "2027-01-01"),
        ("later", "approved", "festival", None),
        ("hidden", "hidden", "festival", None),
        ("place", "approved", "attraction", None),
    ):
        db.execute(text("""
            INSERT INTO public.festivals
                (festival_id, title, region_code, category, source_class_level1, source_class_level2,
                 source_class_code, review_status, published_at, start_date)
            VALUES (:id, '축제', 'SEOUL', :category,
                    CASE WHEN :category = 'festival' THEN 'EV' END,
                    CASE WHEN :category = 'festival' THEN 'EV01' END,
                    CASE WHEN :category = 'festival' THEN 'EV010200' END,
                    :review, now(), CAST(:start AS date))
        """), {"id": ids[key], "category": category, "review": review, "start": start})
    db.execute(text("""
        INSERT INTO public.chat_rooms (room_id, room_type, owner_id, name)
        VALUES (:first_room, 'companion', :first, NULL), (:second_room, 'companion', :second, NULL),
               (:group_room, 'friend_group', :first, '방')
    """), ids)
    db.execute(text("""
        INSERT INTO public.companion_posts
            (post_id, festival_id, author_id, room_id, meet_at, capacity, approved_count, status)
        VALUES (:first_post, :festival, :first, :first_room, now(), 1, 0, 'open'),
               (:second_post, :festival, :second, :second_room, now(), 1, 1, 'full')
    """), ids)
    db.execute(text("""
        INSERT INTO public.companion_applications (application_id, post_id, applicant_id, status, decided_at)
        VALUES (:mine_app, :second_post, :first, 'approved', now()),
               (:other_app, :first_post, :second, 'pending', NULL),
               (:private_app, :second_post, :third, 'pending', NULL)
    """), ids)
    db.execute(text("""
        INSERT INTO public.chat_members (room_id, user_id, role, status, joined_at)
        VALUES (:first_room, :first, 'owner', 'joined', now()),
               (:second_room, :second, 'owner', 'joined', now()),
               (:second_room, :first, 'member', 'joined', now()),
               (:group_room, :first, 'owner', 'joined', now() - interval '2 minutes'),
               (:group_room, :second, 'member', 'joined', now() - interval '1 minute'),
               (:group_room, :third, 'member', 'joined', now())
    """), ids)
    db.execute(text("""
        INSERT INTO public.friend_requests (request_id, from_user, to_user) VALUES (:friend, :second, :first)
    """), ids)
    db.execute(text("""
        INSERT INTO public.friendships (user_a, user_b, request_id) VALUES (:smallest, :largest, :friend)
    """), {**ids, "smallest": min(first, second), "largest": max(first, second)})
    db.execute(text("INSERT INTO public.user_blocks (blocker, blocked) VALUES (:second, :first)"), ids)
    db.execute(text("""
        INSERT INTO public.notifications (user_id, type, ref_type, ref_id)
        VALUES (:first, 'friend_requested', 'friend_request', :friend),
               (:second, 'companion_applied', 'companion_application', :mine_app)
    """), ids)
    db.execute(text("""
        INSERT INTO public.assistant_runs
            (run_id, request_id, conversation_id, user_id, message, answer, run_kind, result)
        VALUES (:run, :run, :conversation, :first, '질문', '답변', 'visit_course', '{"ok": true}'),
               (:other_run, :other_run, :other_conversation, :second, '다른 질문', NULL, 'chat', NULL)
    """), ids)


def test_account_routes_and_withdrawal_with_postgres_rls(client, postgres_account, monkeypatch):
    engine, key, uids = postgres_account
    names = ("a" + key, "b" + key, "c" + key)
    accounts = []
    for name in names:
        account = register_and_login(client, name)
        accounts.append(account)
        uids.append(UUID(account[1]))
    (mine, _, refresh), (other, _, _), _ = accounts
    first, second, third = uids
    credentials = {"email": f"{names[0]}@example.test", "password": PASSWORD}
    second_device, _, second_refresh = login(client, credentials)
    ids = {
        "first": first, "second": second, "third": third,
        **{name: f"fst_{key}{i}" for i, name in enumerate(("festival", "later", "hidden", "place"))},
        **{name: f"crm_{key}{i}" for i, name in enumerate(("first_room", "second_room", "group_room"))},
        "first_post": f"cpo_{key}0", "second_post": f"cpo_{key}1",
        "mine_app": f"cap_{key}0", "other_app": f"cap_{key}1", "private_app": f"cap_{key}2",
        "friend": f"frq_{key}", "run": f"run_{key}0", "other_run": f"run_{key}1",
        "conversation": f"cv_{key}0", "other_conversation": f"cv_{key}1",
    }
    with engine.begin() as db:
        _seed_account_data(db, first, second, ids)

    favorites = f"{ME}/favorites"
    primary = f"{favorites}/{ids['festival']}"
    saved = client.put(primary, headers=mine)
    assert saved.status_code == 201 and "X-Mock" not in saved.headers and saved.json()["is_mock"] is False
    duplicate = client.put(primary, headers=mine)
    assert duplicate.status_code == 200 and duplicate.json() == saved.json()
    assert client.put(f"{favorites}/{ids['later']}", headers=mine).status_code == 201
    for key in ("hidden", "place"):
        assert client.put(f"{favorites}/{ids[key]}", headers=mine).status_code == 404
    assert client.get(favorites, headers=other).json()["total"] == 0
    assert client.delete(primary, headers=other).status_code == 204
    assert client.put(primary, headers=other).status_code == 201
    with engine.begin() as db:
        db.execute(text("INSERT INTO public.favorites (user_id, festival_id) VALUES (:first, :hidden)"), ids)
    listed = client.get(favorites, headers=mine, params={"sort": "start_date"})
    assert listed.status_code == 200 and "X-Mock" not in listed.headers
    assert [entry["festival_id"] for entry in listed.json()["items"]] == [ids["festival"], ids["later"]]
    assert listed.json()["total"] == 2 and listed.json()["is_mock"] is False
    out_of_range = client.get(favorites, headers=mine, params={"page": 3, "page_size": 1}).json()
    assert out_of_range["total"] == 2 and out_of_range["items"] == []

    prefs = f"{ME}/festival-preferences"
    profile = f"{ME}/profile"
    assert client.get(prefs, headers=mine).json() == {
        "scenarios": [], "onboarding_status": "pending", "updated_at": None,
    }
    for headers, scenarios in ((mine, ["solo"]), (other, ["pet"]), (mine, ["solo", "pet"])):
        saved = client.put(prefs, headers=headers, json={"scenarios": scenarios, "skip": False})
        assert saved.status_code == 200 and saved.json()["scenarios"] == scenarios
        assert saved.json()["onboarding_status"] == "completed"
    assert client.get(profile, headers=mine).json() == {
        "user_id": str(first), "display_name": names[0], "birth_year": 2000,
        "gender": "female", "onboarding_status": "completed",
    }
    duplicate_name = client.patch(profile, headers=mine, json={"display_name": names[1].upper()})
    assert duplicate_name.status_code == 409 and duplicate_name.json()["error"]["code"] == "NICKNAME_TAKEN"
    assert client.patch(profile, headers=mine, json={"display_name": "x" + names[0]}).status_code == 200

    activity = f"{ME}/companion-activity"
    posts = client.get(activity, headers=mine, params={"type": "posts"}).json()["items"]
    assert [row["post_id"] for row in posts] == [ids["first_post"]]
    applications = client.get(activity, headers=mine, params={"type": "applications"}).json()["items"]
    assert [row["application_id"] for row in applications] == [ids["mine_app"]]

    async def check_rls():
        async with sessions.user_db_session(first) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            for table in ("profiles", "user_festival_preferences", "favorites"):
                assert not await db.scalar(text(f"SELECT count(*) FROM public.{table} WHERE user_id = :second"), ids)
            denied = await db.execute(text("DELETE FROM public.favorites WHERE user_id = :second"), ids)
            assert denied.rowcount == 0
            assert not await db.scalar(text("""
                SELECT count(*) FROM public.companion_applications WHERE application_id = :private_app
            """), ids)
            # Owning the post grants access to incoming applications, which A79 excludes.
            assert await db.scalar(text("""
                SELECT count(*) FROM public.companion_applications WHERE application_id = :other_app
            """), ids) == 1

    client.portal.call(check_rls)
    rejected = client.request("DELETE", ME, headers=mine, json={"password": "incorrect"})
    assert rejected.status_code == 403
    assert client.get(profile, headers=mine).status_code == 200

    def fail_purge(*_):
        raise RuntimeError("Synthetic transaction failure")

    with monkeypatch.context() as patch:
        patch.setattr(account_deletion, "_purge_assistant_content", fail_purge)
        assert client.request("DELETE", ME, headers=mine, json={"password": PASSWORD}).status_code == 500
    assert client.get(profile, headers=mine).status_code == 200
    assert client.get(favorites, headers=mine).json()["total"] == 2
    assert client.get(activity, headers=mine, params={"type": "posts"}).json()["items"][0]["status"] == "open"

    revoked_claims = tokens.read_access_token(mine["Authorization"])
    assert client.request("DELETE", ME, headers=mine, json={"password": PASSWORD}).status_code == 204
    assert state.get_auth_state().is_revoked(revoked_claims.jti)
    for headers in (mine, second_device):
        assert client.get(profile, headers=headers).status_code == 401
    for token in (refresh, second_refresh):
        assert client.post(f"{AUTH}/refresh", json={"refresh_token": token}).status_code == 401
    assert client.get(prefs, headers=other).json()["scenarios"] == ["pet"]
    assert client.get(favorites, headers=other).json()["total"] == 1

    with engine.connect() as db:
        assert db.execute(text("""
            SELECT email, password_hash, status, display_name, birth_year, gender
            FROM public.users JOIN public.profiles USING (user_id) WHERE user_id = :first
        """), ids).one() == (f"deleted+{first}@invalid", "!", "deleted", None, None, None)
        for table in ("favorites", "user_festival_preferences", "notifications", "refresh_tokens"):
            assert not db.scalar(text(f"SELECT count(*) FROM public.{table} WHERE user_id = :first"), ids)
        for table, columns in (("friendships", "user_a, user_b"), ("friend_requests", "from_user, to_user"),
                               ("user_blocks", "blocker, blocked")):
            assert not db.scalar(text(f"SELECT count(*) FROM public.{table} WHERE :first IN ({columns})"), ids)
        assert db.execute(text("""
            SELECT status, ended_at IS NOT NULL FROM public.companion_posts WHERE post_id = :first_post
        """), ids).one() == ("cancelled", True)
        assert db.execute(text("""
            SELECT status, approved_count FROM public.companion_posts WHERE post_id = :second_post
        """), ids).one() == ("open", 0)
        assert db.scalars(text("""
            SELECT status FROM public.companion_applications WHERE application_id IN (:mine_app, :other_app)
        """), ids).all() == ["cancelled", "cancelled"]
        assert db.execute(text("""
            SELECT status, read_only_at IS NOT NULL FROM public.chat_rooms WHERE room_id = :first_room
        """), ids).one() == ("read_only", True)
        assert db.scalar(text("SELECT owner_id FROM public.chat_rooms WHERE room_id = :group_room"), ids) == second
        assert db.execute(text("""
            SELECT
                (SELECT role FROM public.chat_members WHERE room_id = :group_room AND user_id = :second),
                (SELECT status FROM public.chat_members WHERE room_id = :group_room AND user_id = :first)
        """), ids).one() == ("owner", "left")
        assert db.execute(text("""
            SELECT message, answer, result, purged_at IS NOT NULL FROM public.assistant_runs WHERE run_id = :run
        """), ids).one() == (None, None, None, True)
        assert db.scalar(text("SELECT message FROM public.assistant_runs WHERE run_id = :other_run"), ids) == "다른 질문"
