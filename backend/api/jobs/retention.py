"""DB 설계서 7-0의 일일 보존 정리."""

from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.jobs.purge_chat import delete_expired as delete_expired_chat
from api.repositories.friends import delete_expired_requests

_CHECKPOINT_TABLES = ("checkpoints", "checkpoint_blobs", "checkpoint_writes")


def _delete_expired_checkpoints(db: Session, cutoff: datetime) -> int:
    installed = db.execute(text("""
        SELECT count(*) FROM pg_catalog.pg_tables
        WHERE schemaname = 'langgraph' AND tablename::text = ANY(:tables)
    """), {"tables": list(_CHECKPOINT_TABLES)}).scalar_one()
    if installed == 0:
        return 0
    if installed != len(_CHECKPOINT_TABLES):
        raise RuntimeError("LangGraph 체크포인트 테이블이 일부만 설치되었습니다.")

    # Saver의 저장 도중에는 3개 테이블을 건드리지 않고 다음 실행에서 다시 시도한다.
    db.execute(text("""
        LOCK TABLE langgraph.checkpoints, langgraph.checkpoint_blobs, langgraph.checkpoint_writes
        IN SHARE ROW EXCLUSIVE MODE NOWAIT
    """))
    return db.scalar(text("""
        WITH candidates AS (
            SELECT thread_id FROM langgraph.checkpoints GROUP BY thread_id
            HAVING bool_and(checkpoint->>'ts' IS NOT NULL)
               AND max(CAST(checkpoint->>'ts' AS timestamptz)) <= :cutoff
            UNION
            -- 첫 체크포인트 전에 중단된 저장도 실행 이력으로 만료 시각을 판단한다.
            SELECT a.conversation_id FROM public.assistant_runs a
            WHERE a.queued_at <= :cutoff
              AND NOT EXISTS (SELECT 1 FROM langgraph.checkpoints c WHERE c.thread_id = a.conversation_id)
              AND (
                  EXISTS (SELECT 1 FROM langgraph.checkpoint_writes w WHERE w.thread_id = a.conversation_id)
                  OR EXISTS (SELECT 1 FROM langgraph.checkpoint_blobs b WHERE b.thread_id = a.conversation_id)
              )
        ), expired AS (
            SELECT c.thread_id FROM candidates c
            WHERE NOT EXISTS (
                SELECT 1 FROM public.assistant_runs a WHERE a.conversation_id = c.thread_id
                  AND GREATEST(a.queued_at, a.started_at, a.ended_at) > :cutoff
            )
        ), removed_writes AS (
            DELETE FROM langgraph.checkpoint_writes w USING expired e WHERE w.thread_id = e.thread_id
        ), removed_blobs AS (
            DELETE FROM langgraph.checkpoint_blobs b USING expired e WHERE b.thread_id = e.thread_id
        ), removed_checkpoints AS (
            DELETE FROM langgraph.checkpoints c USING expired e WHERE c.thread_id = e.thread_id
        )
        SELECT count(*) FROM expired
    """), {"cutoff": cutoff})


def sweep(db: Session, now: datetime) -> dict[str, int]:
    cutoff = {"cutoff": now - timedelta(days=30)}
    removed = db.execute(text("""
        DELETE FROM public.route_requests WHERE submitted_at <= :cutoff AND incident_id IS NULL
    """), cutoff).rowcount
    redacted = db.execute(text("""
        UPDATE public.route_requests SET origin_place_hash = NULL, destination_place_hash = NULL
        WHERE submitted_at <= :cutoff AND incident_id IS NOT NULL
          AND (origin_place_hash IS NOT NULL OR destination_place_hash IS NOT NULL)
    """), cutoff).rowcount
    friends = delete_expired_requests(db)
    messages, notifications = delete_expired_chat(db)
    week_ago = now - timedelta(days=7)
    threads = _delete_expired_checkpoints(db, week_ago)
    refresh = db.execute(text("""
        DELETE FROM public.refresh_tokens WHERE GREATEST(expires_at, revoked_at) <= :cutoff
    """), {"cutoff": week_ago}).rowcount
    snapshots = db.execute(text("""
        DELETE FROM public.realtime_snapshots WHERE received_at <= :cutoff
    """), {"cutoff": week_ago}).rowcount
    cache = db.execute(text("""
        DELETE FROM public.route_cache_entries WHERE created_at <= :cutoff
    """), cutoff).rowcount
    trends = db.execute(text("""
        DELETE FROM public.festival_trends WHERE crawled_at <= :cutoff
    """), cutoff).rowcount
    metrics = db.execute(text("""
        DELETE FROM public.route_query_metrics WHERE phase = 'live' AND window_at <= :cutoff
    """), cutoff).rowcount
    assistant_runs = db.execute(text("""
        UPDATE public.assistant_runs
        SET message = NULL, answer = NULL, result = NULL, purged_at = :now
        WHERE purged_at IS NULL AND queued_at <= :cutoff
    """), {**cutoff, "now": now}).rowcount
    return {
        "route_requests": removed, "incident_routes": redacted, "friend_requests": friends,
        "messages": messages, "notifications": notifications, "checkpoint_threads": threads,
        "refresh_tokens": refresh, "realtime_snapshots": snapshots, "route_cache_entries": cache,
        "festival_trends": trends, "route_query_metrics": metrics, "assistant_runs": assistant_runs,
    }
