import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from api.jobs import locks, retention, scheduler

pytestmark = pytest.mark.db


@pytest.fixture
def jobs_engine():
    url = make_url(os.environ.get("TEST_DB_MIGRATION_URL") or os.environ["TEST_DB_URL"]).set(drivername="postgresql+psycopg")
    engine = create_engine(url, hide_parameters=True)
    try:
        yield engine
    finally:
        engine.dispose()


def test_postgres_competing_runners_share_lock_and_success_slot(jobs_engine, monkeypatch):
    @contextmanager
    def service_session():
        with Session(jobs_engine) as db, db.begin():
            db.execute(text("SET LOCAL ROLE noldaga_service"))
            yield db

    entered, release = Event(), Event()

    def run(db, now):
        entered.set()
        assert release.wait(timeout=10)
        return {"processed": 1}

    monkeypatch.setattr(scheduler, "service_db_session", service_session)
    job = scheduler.Job("test_" + uuid4().hex, locks.COMPANIONS, run)
    slot = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        with ThreadPoolExecutor(max_workers=1) as worker:
            future = worker.submit(scheduler._run_once, job, slot, slot)
            try:
                assert entered.wait(timeout=10)
                with pytest.raises(scheduler.JobLocked):
                    scheduler._run_once(job, slot, slot)
            finally:
                release.set()
            assert future.result(timeout=10) == {"processed": 1}
        assert scheduler._run_once(job, slot, slot) is None
    finally:
        with jobs_engine.begin() as db:
            db.execute(text("DELETE FROM public.scheduled_job_runs WHERE job_name = :name"), {"name": job.name})


def test_postgres_daily_route_retention_and_dependencies(jobs_engine):
    suffix = uuid4().hex[:12]
    ids = {"festival": f"fst_{suffix}", "incident": f"inc_{suffix}", "old": f"rr_{suffix}old",
           "fresh": f"rr_{suffix}fresh", "audit": f"rr_{suffix}audit"}
    with Session(jobs_engine) as db:
        db.execute(text("SET LOCAL ROLE noldaga_service"))
        db.execute(text("""
            INSERT INTO public.festivals (festival_id, title, start_date, end_date, region_code)
            VALUES (:festival, '시험 축제', CURRENT_DATE, CURRENT_DATE, '11')
        """), ids)
        db.execute(text("""
            INSERT INTO public.incident_logs
                (incident_id, failure_domain, detected_at, detection_rule, injected_test, before_metrics)
            VALUES (:incident, 'internal_route', now(), 'test', true, '{}')
        """), ids)
        db.execute(text("""
            INSERT INTO public.route_requests
                (route_request_id, request_id, festival_id, origin_type, destination_type,
                 origin_place_hash, destination_place_hash, travel_mode, route_key, status, submitted_at,
                 incident_id, shared_from, access_token_hash, is_mock)
            SELECT id, id, :festival, 'user', 'user', 'hash-a', 'hash-b', 'walk', 'test', 'ready', age,
                   incident_id, shared_from, repeat('a', 64), true
            FROM (VALUES (:old, now() - interval '720 hours', NULL, NULL),
                         (:fresh, now() - interval '719 hours', NULL, :old),
                         (:audit, now() - interval '720 hours', :incident, NULL))
                 AS source(id, age, incident_id, shared_from)
        """), ids)
        db.execute(text("""
            INSERT INTO public.route_results (route_request_id, provider, provider_tier, candidates,
                route_hash, source_type, queried_at, validation_status, is_mock)
            VALUES (:old, 'mock_adapter', 'mock', '[]', 'test', 'fresh', now(), 'verified_basic', true)
        """), ids)
        now = db.scalar(text("SELECT now()"))
        counts = retention.sweep(db, now)
        assert counts["route_requests"] >= 1 and counts["incident_routes"] >= 1
        assert db.execute(text("""
            SELECT route_request_id, origin_place_hash, destination_place_hash, shared_from, status
            FROM public.route_requests WHERE route_request_id IN (:old, :fresh, :audit) ORDER BY route_request_id
        """), ids).all() == [
            (ids["audit"], None, None, None, "ready"),
            (ids["fresh"], "hash-a", "hash-b", None, "ready"),
        ]
        assert db.scalar(text("SELECT count(*) FROM public.route_results WHERE route_request_id = :old"), ids) == 0


def test_postgres_chat_friend_and_notification_cutoffs_and_rls(jobs_engine):
    suffix = uuid4().hex[:12]
    values = {"alice": uuid4(), "bob": uuid4(), "room": f"crm_{suffix}", "old": f"frq_{suffix}old",
              "recent": f"frq_{suffix}recent", "accepted": f"frq_{suffix}kept"}
    values.update(alice_email=f"{values['alice']}@example.test", bob_email=f"{values['bob']}@example.test")
    with Session(jobs_engine) as db:
        db.execute(text("SET LOCAL ROLE noldaga_service"))
        db.execute(text("""
            INSERT INTO public.users (user_id, email, password_hash)
            VALUES (:alice, :alice_email, 'test'), (:bob, :bob_email, 'test')
        """), values)
        db.execute(text("""
            INSERT INTO public.friend_requests (request_id, from_user, to_user, status, responded_at)
            VALUES (:old, :alice, :bob, 'rejected', now() - interval '720 hours'),
                   (:recent, :alice, :bob, 'cancelled', now() - interval '719 hours'),
                   (:accepted, :alice, :bob, 'accepted', now() - interval '721 hours')
        """), values)
        db.execute(text("""
            INSERT INTO public.chat_rooms (room_id, room_type, name, owner_id)
            VALUES (:room, 'friend_group', 'test', :alice)
        """), values)
        db.execute(text("""
            INSERT INTO public.chat_members (room_id, user_id, role, status, joined_at)
            VALUES (:room, :alice, 'owner', 'joined', now() - interval '31 days')
        """), values)
        db.execute(text("""
            INSERT INTO public.chat_messages (room_id, seq, msg_type, body, created_at)
            VALUES (:room, 1, 'system', 'old', now() - interval '720 hours'),
                   (:room, 2, 'system', 'recent', now() - interval '719 hours')
        """), values)
        db.execute(text("""
            INSERT INTO public.notifications (user_id, type, ref_type, ref_id, created_at)
            VALUES (:alice, 'room_invited', 'chat_room', :room, now() - interval '2160 hours'),
                   (:alice, 'room_invited', 'chat_room', :room, now() - interval '2159 hours')
        """), values)
        retention.sweep(db, db.scalar(text("SELECT now()")))
        assert db.execute(text("""
            SELECT seq, body, deleted_at IS NOT NULL FROM public.chat_messages WHERE room_id = :room ORDER BY seq
        """), values).all() == [(1, None, True), (2, "recent", False)]
        assert set(db.execute(text("""
            SELECT request_id FROM public.friend_requests WHERE from_user = :alice
        """), values).scalars()) == {values["recent"], values["accepted"]}

        db.execute(text("SET LOCAL ROLE noldaga_app"))
        for uid, expected in ((values["alice"], 1), (values["bob"], 0)):
            db.execute(text("SELECT set_config('app.user_id', :uid, true)"), {"uid": str(uid)})
            for table in ("notifications", "chat_messages"):
                key = "ref_id" if table == "notifications" else "room_id"
                assert db.scalar(text(f"SELECT count(*) FROM public.{table} WHERE {key} = :room"), values) == expected


def test_postgres_checkpoints_expire_by_latest_thread_activity(jobs_engine):
    suffix = uuid4().hex[:12]
    values = {"old": f"cv_{suffix}old", "active": f"cv_{suffix}active", "queued": f"cv_{suffix}queued",
              "orphan": f"cv_{suffix}orphan", "recent_run": f"run_{suffix}new", "old_run": f"run_{suffix}old"}
    with Session(jobs_engine) as db:
        # 전용 일회용 DB에서 PostgresSaver가 제공하는 테이블 모양을 재현하고 롤백한다.
        db.execute(text("CREATE SCHEMA langgraph"))
        db.execute(text("CREATE TABLE langgraph.checkpoints (thread_id text, checkpoint jsonb)"))
        db.execute(text("CREATE TABLE langgraph.checkpoint_blobs (thread_id text)"))
        db.execute(text("CREATE TABLE langgraph.checkpoint_writes (thread_id text)"))
        db.execute(text("GRANT USAGE ON SCHEMA langgraph TO noldaga_service"))
        db.execute(text("GRANT SELECT, DELETE ON ALL TABLES IN SCHEMA langgraph TO noldaga_service"))
        db.execute(text("""
            INSERT INTO langgraph.checkpoints (thread_id, checkpoint)
            SELECT id, jsonb_build_object('ts', now() - age)
            FROM (VALUES (:old, interval '168 hours'), (:active, interval '169 hours'),
                         (:active, interval '167 hours'), (:queued, interval '169 hours')) AS v(id, age)
        """), values)
        for table in ("checkpoint_blobs", "checkpoint_writes"):
            db.execute(text(f"INSERT INTO langgraph.{table} VALUES (:old), (:active), (:queued), (:orphan)"), values)
        db.execute(text("""
            INSERT INTO public.assistant_runs (run_id, request_id, conversation_id, run_token_hash, message, queued_at)
            VALUES (:recent_run, :recent_run, :queued, 'test', 'test', now()),
                   (:old_run, :old_run, :orphan, 'test', 'test', now() - interval '168 hours')
        """), values)
        db.execute(text("SET LOCAL ROLE noldaga_service"))
        now = db.scalar(text("SELECT now()"))
        assert retention.sweep(db, now)["checkpoint_threads"] == 2
        assert retention.sweep(db, now)["checkpoint_threads"] == 0
        for table in ("checkpoints", "checkpoint_blobs", "checkpoint_writes"):
            assert set(db.execute(text(f"SELECT thread_id FROM langgraph.{table}")).scalars()) == {
                values["active"], values["queued"],
            }


def test_postgres_daily_retention_cutoffs_and_worker_independent_purge(jobs_engine):
    suffix = uuid4().hex[:12]
    args = {"uid": uuid4(), "festival": f"fst_{suffix}", "source": f"test_{suffix}", "key": suffix}
    with Session(jobs_engine) as db:
        db.execute(text("SET LOCAL ROLE noldaga_service"))
        db.execute(text("""
            INSERT INTO public.users (user_id, email, password_hash)
            VALUES (:uid, :key || '@example.test', 'fixture')
        """), args)
        db.execute(text("""
            INSERT INTO public.festivals (festival_id, title, region_code)
            VALUES (:festival, '보존 시험', 'SEOUL')
        """), args)
        db.execute(text("""
            INSERT INTO public.data_sources (source_id, name, scope, is_realtime)
            VALUES (:source, '보존 시험', 'national', true)
        """), args)
        db.execute(text("""
            INSERT INTO public.refresh_tokens (token_id, user_id, token_hash, expires_at, revoked_at)
            VALUES ('rt_' || :key || 'old', :uid, :key || 'old', now() - interval '168 hours', NULL),
                   ('rt_' || :key || 'new', :uid, :key || 'new', now() - interval '167 hours', NULL),
                   ('rt_' || :key || 'revoked', :uid, :key || 'revoked', now() - interval '8 days', now())
        """), args)
        db.execute(text("""
            INSERT INTO public.realtime_snapshots
              (source_id, data_type, target_type, target_id, received_at, payload, payload_hash, sample_kind)
            VALUES (:source, 'weather', 'festival', 'old', now() - interval '168 hours', '{}', 'old', 'mock'),
                   (:source, 'weather', 'festival', 'new', now() - interval '167 hours', '{}', 'new', 'mock')
        """), args)
        db.execute(text("""
            INSERT INTO public.route_cache_entries (cache_key, festival_id, route_hash, provider, created_at, valid_until)
            VALUES (:key || 'old', :festival, 'old', 'mock_adapter', now() - interval '720 hours', now()),
                   (:key || 'new', :festival, 'new', 'mock_adapter', now() - interval '719 hours', now())
        """), args)
        db.execute(text("""
            INSERT INTO public.festival_trends (source_id, crawled_at, raw_title, source_rank, match_status)
            VALUES (:source, now() - interval '720 hours', '만료', 1, 'unmatched'),
                   (:source, now() - interval '719 hours', '유효', 1, 'unmatched')
        """), args)
        db.execute(text("""
            INSERT INTO public.route_query_metrics
              (phase, window_at, offered_requests, accepted_count, valid_completed_count, rejections, timeouts,
               errors, unique_route_keys, backend_execution_count, shared_request_count, cache_hits, is_mock)
            SELECT phase, now() - age, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, true
            FROM (VALUES ('live', interval '720 hours'), ('live', interval '719 hours'),
                         ('fault', interval '720 hours')) AS sample(phase, age)
        """))
        db.execute(text("""
            INSERT INTO public.assistant_runs
              (run_id, request_id, user_id, conversation_id, queued_at, run_status, run_kind,
               message, answer, result)
            SELECT 'run_' || :key || suffix, :key || suffix, :uid, 'cv_' || :key, now() - age,
                   'succeeded', 'visit_course', '질문', '답변', '{}'::jsonb
            FROM (VALUES ('old', interval '720 hours'), ('new', interval '719 hours')) AS sample(suffix, age)
        """), args)

        now = db.scalar(text("SELECT now()"))
        counts = retention.sweep(db, now)
        tables = ("refresh_tokens", "realtime_snapshots", "route_cache_entries", "festival_trends",
                  "route_query_metrics", "assistant_runs")
        assert all(counts[table] >= 1 for table in tables)
        assert db.scalars(text("""
            SELECT token_hash FROM public.refresh_tokens WHERE user_id = :uid ORDER BY token_hash
        """), args).all() == [suffix + "new", suffix + "revoked"]
        assert db.scalars(text("""
            SELECT target_id FROM public.realtime_snapshots WHERE source_id = :source
        """), args).all() == ["new"]
        assert db.scalars(text("""
            SELECT cache_key FROM public.route_cache_entries WHERE festival_id = :festival
        """), args).all() == [suffix + "new"]
        assert db.scalars(text("""
            SELECT raw_title FROM public.festival_trends WHERE source_id = :source
        """), args).all() == ["유효"]
        assert db.execute(text("""
            SELECT phase, window_at FROM public.route_query_metrics
             WHERE window_at IN (now() - interval '719 hours', now() - interval '720 hours')
             ORDER BY phase
        """)).all() == [("fault", now - timedelta(hours=720)), ("live", now - timedelta(hours=719))]
        assert db.execute(text("""
            SELECT run_status, message, answer, result, purged_at FROM public.assistant_runs
             WHERE user_id = :uid ORDER BY queued_at
        """), args).all() == [
            ("succeeded", None, None, None, now),
            ("succeeded", "질문", "답변", {}, None),
        ]
        repeated = retention.sweep(db, now)
        assert all(repeated[table] == 0 for table in tables)
