"""DB-backed A06 dispatch. Claims carry identifiers only, even on retries."""

import json
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text

from api.jobs.assistant_runner import AgentResult, RunInput
from api.repositories.assistant import register, transaction
from api.schemas.assistant import AssistantRequest
from api.services import assistant

ATTEMPT_SECONDS = 30
RETRY_SECONDS = 5
MAX_ATTEMPTS = 2
TOTAL_SECONDS = ATTEMPT_SECONDS * MAX_ATTEMPTS + RETRY_SECONDS
STALLED_SECONDS = 70


@dataclass(frozen=True)
class Claim:
    run_id: str
    attempt: int
    seconds_left: float


class AssistantQueue(Protocol):
    def enqueue(self, query: AssistantRequest, body: object, access: assistant.RunAccess) -> dict[str, object]: ...
    def claim(self) -> Claim | None: ...
    def load(self, claim: Claim) -> RunInput | None: ...
    def step(self, claim: Claim, node: str) -> None: ...
    def finish(self, claim: Claim, result: AgentResult, *, retry: bool = False) -> None: ...
    def maintain(self) -> None: ...


_ACTIVE_CLAIM = """
    run_id = :run_id AND run_status = 'running' AND attempt = :attempt AND purged_at IS NULL
"""


def _claim_params(claim: Claim) -> dict:
    return {"run_id": claim.run_id, "attempt": claim.attempt, "total": TOTAL_SECONDS}


class PostgresAssistantQueue:
    def enqueue(self, query: AssistantRequest, body: object, access: assistant.RunAccess) -> dict[str, object]:
        # A queued assistant_runs insert records the job and makes it claimable in the same commit.
        return register(query, body, access)

    def claim(self) -> Claim | None:
        with transaction() as db:
            row = db.execute(text("""
                WITH due AS (
                    SELECT run_id
                      FROM public.assistant_runs
                     WHERE run_kind = 'chat' AND purged_at IS NULL AND attempt < :max_attempts
                       AND run_status IN ('queued', 'retrying') AND next_attempt_at <= now()
                       AND (started_at IS NULL OR started_at + make_interval(secs => :total) > now())
                     ORDER BY next_attempt_at, run_id
                     LIMIT 1 FOR UPDATE SKIP LOCKED
                )
                UPDATE public.assistant_runs AS runs
                   SET run_status = 'running', attempt = runs.attempt + 1,
                       started_at = COALESCE(runs.started_at, clock_timestamp())
                  FROM due WHERE runs.run_id = due.run_id
                 RETURNING runs.run_id, runs.attempt,
                    EXTRACT(epoch FROM (runs.started_at + make_interval(secs => :total) - clock_timestamp()))
            """), {"max_attempts": MAX_ATTEMPTS, "total": TOTAL_SECONDS}).one_or_none()
        return Claim(row[0], row[1], float(row[2])) if row else None

    def load(self, claim: Claim) -> RunInput | None:
        with transaction() as db:
            row = db.execute(text(f"""
                SELECT request_id, conversation_id, message, execution_context, queued_at
                  FROM public.assistant_runs WHERE {_ACTIVE_CLAIM}
            """), _claim_params(claim)).mappings().one_or_none()
        if row is None:
            return None
        context = dict(row["execution_context"] or {})
        reference_date = context.pop("reference_date", None)
        return RunInput(claim.run_id, AssistantRequest(
            request_id=row["request_id"], conversation_id=row["conversation_id"],
            message=assistant.mask_private_text(row["message"])[:500], context=context,
            reference_date=reference_date or row["queued_at"].astimezone(assistant.KST).date().isoformat(),
        ))

    def step(self, claim: Claim, node: str) -> None:
        if node not in assistant.NODES:
            return
        with transaction() as db:
            db.execute(text(f"""
                SELECT pg_notify(:channel, :payload)
                FROM public.assistant_runs WHERE {_ACTIVE_CLAIM}
                  AND started_at + make_interval(secs => :total) > clock_timestamp()
            """), {
                **_claim_params(claim), "channel": assistant.notify_channel(claim.run_id), "payload": node,
            })

    def finish(self, claim: Claim, result: AgentResult, *, retry: bool = False) -> None:
        with transaction() as db:
            if retry and claim.attempt < MAX_ATTEMPTS:
                rescheduled = db.execute(text(f"""
                    UPDATE public.assistant_runs SET run_status = 'retrying',
                        next_attempt_at = clock_timestamp() + make_interval(secs => :delay)
                    WHERE {_ACTIVE_CLAIM}
                      AND started_at + make_interval(secs => :total)
                          > clock_timestamp() + make_interval(secs => :delay)
                """), {**_claim_params(claim), "delay": RETRY_SECONDS}).rowcount
                if rescheduled:
                    return

            route_id = None
            if result.route_request_id and result.answer and not result.error_code:
                route_id = db.scalar(text("""
                    SELECT r.route_request_id FROM public.route_requests r
                    JOIN public.assistant_runs a ON a.run_id = :run_id
                    WHERE r.route_request_id = :route_id AND r.direction = 'return'
                      AND (r.run_id = a.run_id OR r.route_request_id = a.execution_context->>'route_request_id')
                    FOR KEY SHARE OF r
                """), {"run_id": claim.run_id, "route_id": result.route_request_id})
            route_output = result.route_request_id or any(
                tool.tool in {"request_return_route", "get_route_request_status"} for tool in result.used_tools
            )
            answer = result.answer
            if answer and route_output:
                answer = assistant.ROUTE_ANSWER if route_id else "귀가 화면에서 경로를 확인해 주세요."
            error = result.error_code or (None if answer else assistant.FAILURE_CODE)
            # Respect cancellation/deletion and never let a late attempt replace the terminal state.
            db.execute(text(f"""
                WITH stamp AS (SELECT clock_timestamp() AS at)
                UPDATE public.assistant_runs SET
                    run_status = CASE WHEN CAST(:error AS text) IS NULL AND stamp.at <= started_at + make_interval(secs => :total)
                                      THEN 'succeeded' ELSE 'failed' END,
                    answer = CASE WHEN CAST(:error AS text) IS NULL AND stamp.at <= started_at + make_interval(secs => :total)
                                  THEN :answer END,
                    route_request_id = CASE WHEN stamp.at <= started_at + make_interval(secs => :total)
                                            THEN :route_id END,
                    error_code = CASE WHEN stamp.at > started_at + make_interval(secs => :total)
                                      THEN :failed_code ELSE :error END,
                    error_retryable = :retryable OR stamp.at > started_at + make_interval(secs => :total),
                    used_tools = CAST(:tools AS jsonb), evidence = CAST(:evidence AS jsonb),
                    is_mock = :is_mock, ended_at = stamp.at
                FROM stamp WHERE {_ACTIVE_CLAIM}
            """), {
                **_claim_params(claim), "error": error, "failed_code": assistant.FAILURE_CODE,
                "answer": assistant.mask_private_text(answer) if answer and not error else None,
                "route_id": route_id, "retryable": result.retryable or retry, "is_mock": result.is_mock,
                "tools": json.dumps([tool.model_dump() for tool in result.used_tools]),
                "evidence": json.dumps([item.model_dump(mode="json") for item in result.evidence]) if not error else "[]",
            })

    def maintain(self) -> None:
        with transaction() as db:
            db.execute(text("""
                WITH expired AS (
                    SELECT run_id FROM public.assistant_runs
                     WHERE run_kind = 'chat' AND (
                         (run_status = 'running' AND started_at < now() - make_interval(secs => :stalled))
                         OR (run_status = 'retrying' AND started_at <= now() - make_interval(secs => :total))
                     )
                     LIMIT 100 FOR UPDATE SKIP LOCKED
                )
                UPDATE public.assistant_runs AS a
                   SET run_status = 'failed', error_code = :code, error_retryable = true, ended_at = now()
                  FROM expired WHERE a.run_id = expired.run_id
            """), {"stalled": STALLED_SECONDS, "total": TOTAL_SECONDS, "code": assistant.FAILURE_CODE})

    def purge(self) -> int:
        with transaction() as db:
            return db.execute(text("""
                WITH expired AS (
                    SELECT run_id FROM public.assistant_runs
                     WHERE purged_at IS NULL AND queued_at <= now() - interval '30 days'
                     ORDER BY queued_at, run_id
                     LIMIT 1000 FOR UPDATE SKIP LOCKED
                )
                UPDATE public.assistant_runs AS a
                   SET message = NULL, answer = NULL, result = NULL, purged_at = now()
                  FROM expired WHERE a.run_id = expired.run_id
            """)).rowcount
