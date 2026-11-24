import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state, tokens
from api.ingestion.db import create_ingestion_engine
from api.main import app
from shared.db import session as sessions

pytestmark = pytest.mark.db
AUTH = "/api/v1/auth"


def test_a32_to_a35_postgres_and_rls(monkeypatch):
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
    monkeypatch.setenv("JWT_SECRET", "fixture-postgresql-signing-value-for-tests")
    for key in ("ACCESS_JWT_TTL_MIN", "REFRESH_TTL_DAYS", "AUTH_RATE_LIMIT_PER_MIN", "REFRESH_LOCK_TTL_S"):
        monkeypatch.delenv(key, raising=False)

    run_id = uuid4().hex
    password = "PostgresFixture123"
    people = [
        {"email": f"{run_id}-{i}@example.test", "password": password,
         "display_name": f"{i}{run_id[:9]}", "birth_year": 2000, "gender": "female"}
        for i in range(3)
    ]
    emails = [person["email"] for person in people]

    def login(client, person):
        response = client.post(f"{AUTH}/login", json={"email": person["email"].upper(), "password": password})
        assert response.status_code == 200
        return response.json()

    def refresh(client, token):
        return client.post(f"{AUTH}/refresh", json={"refresh_token": token})

    async def visible_profiles(user_id, other_id):
        async with sessions.user_db_session(user_id) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            assert not await db.scalar(text("SELECT has_table_privilege('public.users', 'SELECT')"))
            assert not await db.scalar(text("SELECT has_table_privilege('public.refresh_tokens', 'SELECT')"))
            ids = (await db.scalars(text("""
                SELECT user_id FROM public.profiles WHERE user_id IN (:own, :other)
            """), {"own": user_id, "other": other_id})).all()
            return ids

    try:
        with TestClient(app) as client:
            try:
                ids = []
                for person in people[:2]:
                    result = client.post(f"{AUTH}/signup", json=person)
                    assert result.status_code == 201 and "X-Mock" not in result.headers
                    ids.append(UUID(result.json()["user_id"]))

                duplicate = client.post(f"{AUTH}/signup", json=people[0])
                assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
                duplicate = client.post(f"{AUTH}/signup", json={
                    **people[2], "display_name": people[0]["display_name"].upper(),
                })
                assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "NICKNAME_TAKEN"
                with service_engine.connect() as db:
                    assert db.scalar(text("SELECT count(*) FROM public.users WHERE email = :email"),
                                     {"email": emails[2]}) == 0

                first, another_device, other_account = (
                    login(client, people[0]), login(client, people[0]), login(client, people[1]),
                )
                with service_engine.connect() as db:
                    saved = db.execute(text("""
                        SELECT u.email, u.password_hash, u.last_login_at, u.status, p.display_name, p.role,
                               p.birth_year, p.gender, t.token_hash, t.expires_at, t.revoked_at, t.token_id
                        FROM public.users u JOIN public.profiles p USING (user_id)
                        JOIN public.refresh_tokens t USING (user_id) WHERE t.token_hash = :digest
                    """), {"digest": tokens.refresh_hash(first["refresh_token"])}).one()
                assert saved.email == emails[0] and saved.status == "active" and saved.last_login_at
                assert tokens.password_matches(password, saved.password_hash)
                assert saved.role == "user" and saved.display_name == people[0]["display_name"]
                assert (saved.birth_year, saved.gender) == (2000, "female")
                assert saved.token_id.startswith("rt_") and len(saved.token_id) == 29
                assert saved.token_hash != first["refresh_token"] and saved.revoked_at is None
                assert client.portal.call(visible_profiles, *ids) == ids[:1]

                with service_engine.begin() as db:
                    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:token_id, 0))"),
                               {"token_id": saved.token_id})
                    busy = refresh(client, first["refresh_token"])
                    assert busy.status_code == 409 and busy.json()["error"]["code"] == "REFRESH_IN_PROGRESS"
                rotated = refresh(client, first["refresh_token"])
                assert rotated.status_code == 200
                reused = refresh(client, first["refresh_token"])
                assert reused.status_code == 401 and reused.json()["error"]["code"] == "REFRESH_REUSED"
                with service_engine.connect() as db:
                    active = db.execute(text("""
                        SELECT user_id FROM public.refresh_tokens
                        WHERE user_id IN (:own, :other) AND revoked_at IS NULL
                    """), {"own": ids[0], "other": ids[1]}).scalars().all()
                    assert active == ids[1:]
                assert refresh(client, another_device["refresh_token"]).status_code == 401
                assert refresh(client, rotated.json()["refresh_token"]).status_code == 401

                other_device = login(client, people[1])
                body = {"refresh_token": other_account["refresh_token"]}
                authorization = {"Authorization": f"Bearer {other_account['access_token']}"}
                assert client.post(f"{AUTH}/logout", json=body, headers=authorization).status_code == 204
                assert client.post(f"{AUTH}/logout", json=body, headers=authorization).status_code == 401
                with service_engine.connect() as db:
                    assert db.scalar(text("""
                        SELECT revoked_at IS NOT NULL FROM public.refresh_tokens WHERE token_hash = :digest
                    """), {"digest": tokens.refresh_hash(other_account["refresh_token"])})
                assert refresh(client, other_device["refresh_token"]).status_code == 200

                disabled = login(client, people[0])
                with service_engine.begin() as db:
                    db.execute(text("UPDATE public.users SET status = 'disabled' WHERE user_id = :id"), {"id": ids[0]})
                response = client.post(f"{AUTH}/logout", json={"refresh_token": disabled["refresh_token"]},
                                       headers={"Authorization": f"Bearer {disabled['access_token']}"})
                assert response.status_code == 401
            finally:
                client.portal.call(user_engine.dispose)
    finally:
        try:
            with service_engine.begin() as db:
                for table in ("refresh_tokens", "profiles"):
                    db.execute(text(f"""
                        DELETE FROM public.{table} WHERE user_id IN (
                            SELECT user_id FROM public.users WHERE email IN (:first, :second, :third)
                        )
                    """), dict(zip(("first", "second", "third"), emails)))
                db.execute(text("DELETE FROM public.users WHERE email IN (:first, :second, :third)"),
                           dict(zip(("first", "second", "third"), emails)))
        finally:
            service_engine.dispose()
