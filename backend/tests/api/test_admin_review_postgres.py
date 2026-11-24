import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state, tokens
from api.ingestion.db import create_ingestion_engine
from shared.db import session as sessions

from .test_admin_review import PATH

pytestmark = pytest.mark.db


@pytest.fixture
def review_database(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or url).set(drivername="postgresql+psycopg")
    service_engine = create_ingestion_engine(url)
    user_engine = create_async_engine(app_url, hide_parameters=True)

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
    monkeypatch.setenv("JWT_SECRET", "fixture-a24-postgresql-signing-value")

    roles = {role: uuid4() for role in ("admin", "operator", "user")}
    festivals = {key: f"fst_{uuid4().hex[:20]}" for key in ("coords", "race", "reject")}
    queue = {}
    try:
        with service_engine.begin() as db:
            assert db.scalar(text("SELECT current_user")) == "noldaga_service"
            for role, user_id in roles.items():
                params = {"id": user_id, "email": f"{user_id}@example.test", "role": role}
                db.execute(text("INSERT INTO public.users (user_id, email, password_hash) VALUES (:id, :email, '!')"),
                           params)
                db.execute(text("INSERT INTO public.profiles (user_id, role) VALUES (:id, :role)"), params)
            for key, festival_id in festivals.items():
                db.execute(text("""
                    INSERT INTO public.festivals
                      (festival_id, title, region_code, category, source_class_level2, address)
                    VALUES (:id, '검토 시험 축제', 'SEOUL', 'festival', 'EV01', '서울')
                """), {"id": festival_id})
                queue[key] = db.scalar(text("""
                    INSERT INTO public.festival_review_queue (festival_id, reason, proposed_value)
                    VALUES (:id, 'coords_out_of_range', '{"latitude":37.5,"longitude":127,"coords_source":"geocoded"}')
                    RETURNING queue_id
                """), {"id": festival_id})

        headers = {
            role: {"Authorization": "Bearer " + tokens.issue_access_token(
                user_id, "user", datetime.now(timezone.utc), 1800,
            )}
            for role, user_id in roles.items()
        }
        yield service_engine, headers, roles, festivals, queue
    finally:
        client.portal.call(user_engine.dispose)
        try:
            with service_engine.begin() as db:
                for table in ("festival_review_queue", "festival_change_history", "festivals"):
                    db.execute(text(f"DELETE FROM public.{table} WHERE festival_id = ANY(:ids)"),
                               {"ids": list(festivals.values())})
                for table in ("profiles", "users"):
                    db.execute(text(f"DELETE FROM public.{table} WHERE user_id = ANY(:ids)"),
                               {"ids": list(roles.values())})
        finally:
            service_engine.dispose()


def test_a24_service_role_rls_decisions_and_concurrency(client, review_database):
    engine, headers, roles, festivals, queue = review_database

    async def check_rls(expected_public):
        async with sessions.user_db_session(roles["operator"]) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            assert await db.scalar(text("""
                SELECT count(*) FROM public.profiles WHERE user_id = :other
            """), {"other": roles["admin"]}) == 0
            visible = (await db.scalars(text("""
                SELECT festival_id FROM public.festivals WHERE festival_id = ANY(:ids)
            """), {"ids": list(festivals.values())})).all()
            assert visible == expected_public
            with pytest.raises(DBAPIError) as error:
                async with db.begin_nested():
                    await db.execute(text("SELECT queue_id FROM public.festival_review_queue"))
            assert error.value.orig.sqlstate == "42501"

    client.portal.call(check_rls, [])
    assert client.get(PATH).status_code == 401
    assert client.get(PATH, headers=headers["user"]).status_code == 403
    listed = client.get(PATH, headers=headers["operator"], params={"reason": "coords_out_of_range"})
    assert listed.status_code == 200 and "X-Mock" not in listed.headers
    assert set(queue.values()) <= {item["queue_id"] for item in listed.json()["items"]}

    def decide(key, decision, role, **extra):
        return client.post(PATH, headers=headers[role], json={
            "queue_id": queue[key], "decision": decision, "note": "검토 근거", **extra,
        })

    assert decide("coords", "approve", "user").status_code == 403
    invalid = decide("coords", "approve", "operator", value={"longitude": 127})
    assert invalid.status_code == 422 and "X-Mock" not in invalid.headers
    approved = decide("coords", "approve", "operator")
    assert approved.json() == {"queue_id": queue["coords"], "approval_status": "approved", "applied": True}
    rejected = decide("reject", "reject", "admin")
    assert rejected.json() == {"queue_id": queue["reject"], "approval_status": "rejected", "applied": False}

    barrier = Barrier(2, timeout=5)

    def hide(role):
        barrier.wait()
        return decide("race", "hide", role)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(hide, ("operator", "admin")))
    assert sorted(response.status_code for response in outcomes) == [200, 409]
    assert next(response for response in outcomes if response.status_code == 409).json()["error"]["code"] == (
        "ALREADY_REVIEWED"
    )

    client.portal.call(check_rls, [festivals["coords"]])
    with engine.connect() as db:
        rows = {row["festival_id"]: row for row in db.execute(text("""
            SELECT f.*, q.reviewer, q.reviewed_at
            FROM public.festivals f JOIN public.festival_review_queue q USING (festival_id)
            WHERE queue_id = ANY(:ids)
        """), {"ids": list(queue.values())}).mappings()}
        published, hidden, unchanged = (rows[festivals[key]] for key in ("coords", "race", "reject"))
        assert published["review_status"] == "approved" and published["published_at"] is not None
        assert (published["latitude"], published["longitude"], published["coords_source"]) == (37.5, 127, "geocoded")
        assert published["reviewer"] == roles["operator"] and published["reviewed_at"] is not None
        assert (hidden["review_status"], hidden["published_at"]) == ("hidden", None)
        assert (unchanged["review_status"], unchanged["published_at"], unchanged["reviewer"]) == (
            "pending", None, roles["admin"],
        )
        audits = db.execute(text("""
            SELECT after_value FROM public.festival_change_history
            WHERE festival_id = ANY(:ids) AND field = 'review_decision' AND actor = 'admin'
        """), {"ids": list(festivals.values())}).scalars().all()
        assert len(audits) == 3
        assert {row["decision"] for row in audits} == {"approve", "reject", "hide"}
        assert all(row["reason"] == "검토 근거" for row in audits)
