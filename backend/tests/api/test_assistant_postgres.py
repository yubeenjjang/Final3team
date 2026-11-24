import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Event
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from api.auth import state, tokens
from api.jobs.assistant_queue import PostgresAssistantQueue
from api.jobs.assistant_runner import AgentResult
from api.jobs.assistant_worker import work_once
from api.realtime import job_events
from api.repositories import assistant as store
from api.schemas.assistant import AssistantRequest
from api.services import assistant
from shared.db import session as sessions

from .test_assistant_worker import QUERY, run_headers, submit

pytestmark = pytest.mark.db


@pytest.fixture
def database(client, monkeypatch):
    url = make_url(os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    app_url = make_url(os.environ.get("TEST_DB_APP_URL") or os.environ["TEST_DB_URL"])
    service = create_engine(url, hide_parameters=True)
    app = create_async_engine(app_url.set(drivername="postgresql+psycopg"), hide_parameters=True)
    ids = [uuid4(), uuid4()]
    prefix = f"a06-{uuid4()}"

    @event.listens_for(service, "begin")
    def assume_service(connection):
        connection.exec_driver_sql("SET LOCAL ROLE noldaga_service")

    if not os.environ.get("TEST_DB_APP_URL"):
        @event.listens_for(app.sync_engine, "begin")
        def assume_app(connection):
            connection.exec_driver_sql("SET LOCAL ROLE noldaga_app")

    async def connect():
        conn = await psycopg.AsyncConnection.connect(
            url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True,
        )
        await conn.execute("SET ROLE noldaga_service")
        return conn

    monkeypatch.setattr(sessions, "_service_engine", lambda: service)
    monkeypatch.setattr(sessions, "_user_engine", lambda: app)
    monkeypatch.setattr(state, "_auth_state", state.MemoryAuthState())
    monkeypatch.setattr(job_events, "_listen_connection", connect)
    monkeypatch.setenv("ASSISTANT_PROVIDER", "db")
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("JWT_SECRET", "isolated-assistant-db-fixture-jwt")
    monkeypatch.setenv("ASSISTANT_TOKEN_SECRET", "isolated-assistant-db-fixture-token")
    try:
        with service.begin() as db:
            for uid in ids:
                db.execute(text("INSERT INTO public.users (user_id, email, password_hash) VALUES (:uid, :mail, 'fixture')"),
                           {"uid": uid, "mail": f"{uid}@example.test"})
                db.execute(text("INSERT INTO public.profiles (user_id, display_name) VALUES (:uid, :name)"),
                           {"uid": uid, "name": uid.hex[:12]})
        now = datetime.now(timezone.utc)
        headers = [{"Authorization": f"Bearer {tokens.issue_access_token(uid, 'user', now, 600)}"} for uid in ids]
        yield service, (ids[0], ids[1]), headers, prefix
    finally:
        with service.begin() as db:
            db.execute(text("DELETE FROM public.assistant_runs WHERE request_id LIKE :prefix"), {"prefix": prefix + "%"})
            db.execute(text("DELETE FROM public.profiles WHERE user_id IN (:a, :b)"), dict(zip(("a", "b"), ids)))
            db.execute(text("DELETE FROM public.users WHERE user_id IN (:a, :b)"), dict(zip(("a", "b"), ids)))
        client.portal.call(app.dispose)
        service.dispose()


def test_db_api_owner_idempotency_and_rls(client, database):
    service, (alice, bob), (owner, other), prefix = database
    body = {"request_id": prefix, "message": "연락처는 010-1234-5678"}
    response = client.post(QUERY, json=body, headers=owner)
    assert response.status_code == 202
    run = response.json()
    assert run["run_status"] == "queued"
    assert "X-Mock" not in response.headers
    assert client.post(QUERY, json=body, headers=owner).json() == run
    assert client.post(QUERY, json=body, headers=other).status_code == 403
    assert client.post(QUERY, json={**body, "message": "변경"}, headers=owner).status_code == 409
    assert client.get(run["status_url"], headers=other).status_code == 403
    assert client.get(run["status_url"], headers=run_headers(run)).status_code == 403
    assert client.get(run["events_url"], headers=other).status_code == 403
    assert client.get("/api/v1/assistant/runs/run_zzzzzz", headers=owner).status_code == 404
    with service.begin() as db:
        row = db.execute(text("""
            SELECT message, run_token_hash, attempt FROM public.assistant_runs WHERE run_id = :run_id
        """), {"run_id": run["run_id"]}).one()
        assert row.message == "연락처는 [연락처]"
        assert row.run_token_hash == assistant.digest(run["run_access_token"])
        assert row.attempt == 0

    async def verify(uid, expected):
        async with sessions.user_db_session(uid) as db:
            assert await db.scalar(text("SELECT current_user")) == "noldaga_app"
            assert await db.scalar(text("SELECT count(*) FROM public.assistant_runs WHERE run_id = :run_id"),
                                  {"run_id": run["run_id"]}) == expected

    client.portal.call(verify, alice, 1)
    client.portal.call(verify, bob, 0)
    queue = PostgresAssistantQueue()
    assert work_once(queue, lambda claim: (AgentResult(answer="이메일 user@example.test", is_mock=True), False))
    result = client.get(run["status_url"], headers=owner).json()
    assert result["run_status"] == "succeeded" and result["is_mock"]
    assert result["answer"] == "이메일 [연락처]"
    assert client.post(QUERY, json=body, headers=owner).json()["run_status"] == "succeeded"


def test_db_concurrent_registration_claim_retry_and_cleanup(database):
    service, (alice, _), _, prefix = database
    access = assistant.RunAccess(alice)
    query = AssistantRequest(request_id=prefix, message="축제")
    body = query.model_dump()
    queue = PostgresAssistantQueue()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.register(query, body, access), range(8)))
        assert all(result == results[0] for result in results)
        claims = [claim for claim in pool.map(lambda _: queue.claim(), range(8)) if claim is not None]
    assert len(claims) == 1
    first = claims[0]
    assert first.run_id == results[0]["run_id"] and first.attempt == 1
    assert queue.load(first).query.message == "축제"
    queue.finish(first, AgentResult(error_code="AI_AGENT_FAILED"), retry=True)
    assert queue.claim() is None
    with service.begin() as db:
        params = {"rid": first.run_id}
        assert db.scalar(text("""
            SELECT run_status = 'retrying' AND next_attempt_at >= now() + interval '4 seconds'
            FROM public.assistant_runs WHERE run_id = :rid
        """), params)
        db.execute(text("UPDATE public.assistant_runs SET next_attempt_at = now() - interval '1 second' WHERE run_id = :rid"),
                   params)
    second = queue.claim()
    assert second.run_id == first.run_id and second.attempt == 2
    assert queue.claim() is None
    queue.finish(first, AgentResult(answer="늦은 응답"))
    with service.begin() as db:
        db.execute(text("UPDATE public.assistant_runs SET started_at = now() - interval '71 seconds' WHERE run_id = :rid"),
                   params)
    queue.maintain()
    queue.finish(second, AgentResult(answer="정리 뒤 응답"))
    with service.begin() as db:
        assert db.execute(text("""
            SELECT run_status, attempt, answer, error_code FROM public.assistant_runs WHERE run_id = :rid
        """), params).one() == ("failed", 2, None, "AI_AGENT_FAILED")
        db.execute(text("UPDATE public.assistant_runs SET queued_at = now() - interval '31 days' WHERE run_id = :rid"),
                   params)
    assert queue.purge() == 1
    with service.begin() as db:
        assert db.scalar(text("""
            SELECT purged_at IS NOT NULL AND message IS NULL AND execution_context IS NULL
            FROM public.assistant_runs WHERE run_id = :rid
        """), params)


def test_db_live_sse_across_database_connections(client, database, monkeypatch):
    _, _, _, prefix = database
    run = submit(client, request_id=prefix).json()
    assert client.get(run["events_url"]).status_code == 401
    assert client.get(run["events_url"], headers={"X-Run-Access-Token": "wrong"}).status_code == 403
    queue = PostgresAssistantQueue()
    subscribed = Event()
    snapshot = job_events._snapshot

    async def mark_ready(run_id, access):
        result = await snapshot(run_id, access)
        subscribed.set()
        return result

    monkeypatch.setattr(job_events, "_snapshot", mark_ready)
    monkeypatch.setattr(job_events, "_KEEPALIVE_SECONDS", 0.5)
    with ThreadPoolExecutor(max_workers=1) as pool:
        stream = pool.submit(client.get, run["events_url"], headers=run_headers(run))
        assert subscribed.wait(4)
        claim = queue.claim()
        assert claim.run_id == run["run_id"]
        queue.step(claim, "festival")
        queue.finish(claim, AgentResult(answer="축제 소식"))
        response = stream.result(timeout=8)
    assert response.status_code == 200
    assert 'event: step\ndata: {"type": "step", "node": "festival"}' in response.text
    assert 'event: token\ndata: {"type": "token", "text": "축제 소식"}' in response.text
    assert response.text.endswith('event: done\ndata: {"type": "done"}\n\n')
