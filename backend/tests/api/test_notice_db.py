import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth.tokens import issue_access_token
from api.ingestion.db import create_ingestion_engine
from api.providers.route_base import KST
from api.repositories import festival_info
from api.repositories.notices import postgres_store
from api.services import festival_store
from shared.db import session as sessions

pytestmark = pytest.mark.db
ADMIN = "/api/v1/admin/notices"


def test_postgres_notice_roles_rls_concurrent_review_and_schedule(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or os.environ["TEST_DB_URL"])
    app_url = app_url.set(drivername="postgresql+psycopg")
    service_engine = create_ingestion_engine(url)
    app_engine = create_ingestion_engine(app_url)
    user_engine = create_async_engine(app_url, hide_parameters=True)

    @event.listens_for(service_engine, "begin")
    def set_service_role(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    if not os.environ.get("TEST_DB_APP_URL"):
        @event.listens_for(app_engine, "begin")
        @event.listens_for(user_engine.sync_engine, "begin")
        def set_app_role(connection):
            connection.exec_driver_sql("SET LOCAL ROLE noldaga_app")

    monkeypatch.setattr(sessions, "_service_engine", lambda: service_engine)
    monkeypatch.setattr(sessions, "_user_engine", lambda: user_engine)
    monkeypatch.setattr(festival_store, "get_festival_engine", lambda: app_engine)
    monkeypatch.setattr(festival_info, "get_festival_engine", lambda: app_engine)
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setenv("JWT_SECRET", "notice-db-fixture-signing-value-for-tests")

    actors = {"operator": uuid4(), "admin": uuid4(), "user": uuid4()}
    festival_id = "fst_" + uuid4().hex[:20]
    now = datetime.now(KST)
    starts = now + timedelta(hours=1)
    ends = now + timedelta(hours=2)

    def headers(role):
        # 토큰 role이 admin이어도 본인 RLS 세션에서 읽은 프로필 역할로 결정한다.
        token = issue_access_token(actors[role], "admin", now, 300)
        return {"Authorization": f"Bearer {token}"}

    try:
        with service_engine.begin() as db:
            for role, user_id in actors.items():
                db.execute(text("""
                    INSERT INTO public.users (user_id, email, password_hash) VALUES (:id, :email, '!')
                """), {"id": user_id, "email": f"{user_id}@example.test"})
                db.execute(text("""
                    INSERT INTO public.profiles (user_id, role) VALUES (:id, :role)
                """), {"id": user_id, "role": role})
            db.execute(text("""
                INSERT INTO public.festivals
                  (festival_id, title, region_code, category, source_class_level2, review_status, published_at)
                VALUES (:id, '합성 축제', 'SEOUL', 'festival', 'EV01', 'approved', now())
            """), {"id": festival_id})
        payload = {
            "festival_id": festival_id, "type": "no_stop", "title": "동시 승인 검증",
            "content": "합성 공지입니다.", "source_url": "https://example.test/official",
            "effective_from": starts.isoformat(), "effective_to": ends.isoformat(),
        }
        assert client.post(ADMIN, json=payload, headers=headers("user")).status_code == 403
        created = client.post(ADMIN, json=payload, headers=headers("operator"))
        assert created.status_code == 201 and "X-Mock" not in created.headers
        notice_id = created.json()["notice_id"]

        with app_engine.begin() as db:
            db.execute(text("SELECT set_config('app.user_id', :id, true)"), {"id": str(actors["user"])})
            assert db.scalar(text("SELECT current_user")) == "noldaga_app"
            assert db.scalar(text("SELECT count(*) FROM public.profiles WHERE user_id = :id"),
                             {"id": actors["operator"]}) == 0
            assert db.scalar(text("SELECT count(*) FROM public.official_notices WHERE notice_id = :id"),
                             {"id": notice_id}) == 0
            assert not db.scalar(text("SELECT has_table_privilege('public.notice_events', 'SELECT')"))

        barrier = Barrier(2, timeout=5)

        def approve(role):
            barrier.wait()
            return client.post(f"{ADMIN}/{notice_id}/review", json={"decision": "approve"}, headers=headers(role))

        with ThreadPoolExecutor(max_workers=2) as pool:
            reviews = list(pool.map(approve, ("operator", "admin")))
        assert sorted(result.status_code for result in reviews) == [200, 409]
        reject = next(result for result in reviews if result.status_code == 409)
        assert reject.json()["error"]["code"] == "ALREADY_REVIEWED"

        public = f"/api/v1/festivals/{festival_id}/notices"
        assert client.get(public).json()["items"] == []
        listed = client.get(public, params={"active_only": False}).json()["items"]
        assert [item["notice_id"] for item in listed] == [notice_id]

        def revision(at):
            return int(postgres_store.snapshot(festival_id, at).version.removeprefix("cv"))

        approval_version = revision(datetime.now(KST))
        assert revision(starts) == approval_version + 1
        assert revision(ends) == approval_version + 2
        assert postgres_store.snapshot(festival_id, starts).titles == (payload["title"],)
        assert postgres_store.snapshot(festival_id, ends).titles == ()

        close = client.post(f"{ADMIN}/{notice_id}/end", headers=headers("admin"))
        assert close.status_code == 200
        assert revision(ends) == approval_version + 1
        with service_engine.connect() as db:
            actions = db.execute(text("""
                SELECT action FROM public.notice_events WHERE notice_id = :id ORDER BY event_id
            """), {"id": notice_id}).scalars().all()
            assert actions == ["create", "approve", "end"]
    finally:
        # 동시 요청에는 커밋이 필요하므로 일회용 DB가 종료 이력까지 함께 정리한다.
        client.portal.call(user_engine.dispose)
        app_engine.dispose()
        service_engine.dispose()
