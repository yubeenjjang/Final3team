"""A06 registration and RLS-aware status reads."""

import hmac
import json
import os
from base64 import b32encode
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from ulid import ULID

from api.auth.tokens import unauthorized
from api.schemas.assistant import AssistantRequest
from api.services import assistant
from shared.db.session import service_db_session

_STATUS = """
    SELECT run_id, conversation_id, run_kind, run_status, answer, used_tools, evidence,
           result, route_request_id, error_code, error_retryable, queued_at,
           started_at, ended_at, is_mock
      FROM public.assistant_runs WHERE run_id = :run_id
"""
_ROUTE = """
    SELECT access_token_hash, submitted_at
      FROM public.route_requests
     WHERE route_request_id = :route_id AND direction = 'return' AND request_body_hash IS NOT NULL
"""


@contextmanager
def transaction():
    try:
        with service_db_session() as db:
            yield db
    except (SQLAlchemyError, ValueError):
        raise assistant.unavailable() from None


def _assistant_secret() -> bytes:
    key = os.environ.get("ASSISTANT_TOKEN_SECRET", "").encode()
    if len(key.strip()) < 32:
        raise assistant.unavailable()
    return key


def _access_token(key: bytes, run_id: str) -> str:
    return "rat_" + b32encode(hmac.digest(key, f"run-token:{run_id}".encode(), "sha256")).decode()[:32]


def _check_conversation(db, conversation_id: str, access: assistant.RunAccess) -> None:
    params = {"conversation_id": conversation_id}
    if access.user_id is not None:
        owner = db.scalar(text("""
            SELECT 1 FROM public.assistant_runs
            WHERE conversation_id = :conversation_id AND user_id = :user_id AND purged_at IS NULL LIMIT 1
        """), {**params, "user_id": access.user_id})
        if owner is None:
            raise assistant.forbidden()
        return
    if not access.run_token:
        raise assistant.forbidden()
    row = db.execute(text("""
        SELECT user_id, run_token_hash, queued_at FROM public.assistant_runs
        WHERE conversation_id = :conversation_id AND user_id IS NULL
          AND run_token_hash = :token_hash AND purged_at IS NULL
    """), {**params, "token_hash": access.token_hash}).first()
    if row is None:
        raise assistant.forbidden()
    assistant.authorize_run(*row, access)


def _verify_route_context(db, route_id: str, token: str | None) -> None:
    from api.repositories.route_store import TOKEN_TTL

    row = db.execute(text(_ROUTE), {"route_id": route_id}).one_or_none()
    if not token or row is None or not assistant.matches(row.access_token_hash, assistant.digest(token)):
        raise assistant.forbidden()
    if assistant.now() >= row.submitted_at + TOKEN_TTL:
        raise ApiError(401, "UNAUTHORIZED", "경로 조회 토큰이 만료됐어요.")


def register(command: AssistantRequest, body: object, access: assistant.RunAccess) -> dict[str, object]:
    key = _assistant_secret()
    body_hash = hmac.digest(key, b"request:" + assistant.canonical_body(body).encode(), "sha256").hex()
    run_id = f"run_{ULID()}"
    conversation_id = command.conversation_id or f"cv_{ULID()}"
    token = _access_token(key, run_id)
    with transaction() as db:
        if access.user_id is not None:
            # A80 takes FOR NO KEY UPDATE on the same row before purging assistant content.
            status = db.scalar(text("SELECT status FROM public.users WHERE user_id = :uid FOR SHARE"),
                               {"uid": access.user_id})
            if status != "active":
                raise unauthorized()
        params = {"request_id": command.request_id}
        # Serialize registrations sharing the globally unique request_id (including replays).
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:request_id, 6006))"), params)
        existing = db.execute(text("""
            SELECT run_id, conversation_id, run_kind, run_status, user_id, run_token_hash, queued_at,
                   request_body_hash, anonymous_session_hash, is_mock
            FROM public.assistant_runs WHERE request_id = :request_id
        """), params).mappings().one_or_none()
        if existing is not None:
            assistant.authorize_replay(existing["user_id"], existing["anonymous_session_hash"],
                                       existing["run_token_hash"], existing["queued_at"], access)
            if existing["run_kind"] != "chat" or not assistant.matches(existing["request_body_hash"], body_hash):
                raise assistant.conflict()
            return assistant.accepted(
                existing["run_id"], existing["conversation_id"], existing["run_status"],
                _access_token(key, existing["run_id"]), existing["is_mock"],
            )

        if command.conversation_id:
            _check_conversation(db, command.conversation_id, access)
        if command.context.route_request_id:
            _verify_route_context(db, command.context.route_request_id, access.route_token)
        context = {
            **command.context.model_dump(),
            "reference_date": command.reference_date or assistant.now().astimezone(assistant.KST).date().isoformat(),
        }
        inserted = db.execute(text("""
            INSERT INTO public.assistant_runs (
                run_id, request_id, user_id, run_token_hash, conversation_id, message,
                request_body_hash, anonymous_session_hash, execution_context
            )
            VALUES (
                :run_id, :request_id, :user_id, :run_token_hash, :conversation_id, :message,
                :body_hash, :session_hash, CAST(:context AS jsonb)
            )
            ON CONFLICT (request_id) DO NOTHING
            RETURNING run_id
        """), {
            **params, "run_id": run_id, "user_id": access.user_id, "run_token_hash": assistant.digest(token),
            "conversation_id": conversation_id, "message": assistant.mask_private_text(command.message)[:500],
            "body_hash": body_hash, "session_hash": access.session_hash, "context": json.dumps(context),
        }).scalar_one_or_none()
        if inserted is None:
            # A different run producer may share the request ID without taking the A06 lock.
            raise assistant.conflict()
    return assistant.accepted(run_id, conversation_id, "queued", token, False)


def _has_run(run_id: str) -> bool:
    with transaction() as db:
        return db.scalar(text("SELECT 1 FROM public.assistant_runs WHERE run_id = :run_id"), {"run_id": run_id}) is not None


def _route_access_token(route_id: str) -> str | None:
    from api.services.real_routes import stored_route_access_token

    with transaction() as db:
        row = db.execute(text(_ROUTE), {"route_id": route_id}).one_or_none()
        return stored_route_access_token(route_id, *row) if row else None


def _read_anonymous(run_id: str, access: assistant.RunAccess) -> dict[str, object]:
    with transaction() as db:
        params = {"run_id": run_id}
        # One snapshot keeps authorization and the returned state consistent.
        row = db.execute(text(f"""
            SELECT status.*, owner.user_id, owner.run_token_hash
            FROM ({_STATUS}) status JOIN public.assistant_runs owner USING (run_id)
        """), params).mappings().one_or_none()
        if row is None:
            raise assistant.not_found()
        assistant.authorize_run(row["user_id"], row["run_token_hash"], row["queued_at"], access)
        return dict(row)


async def read(
    run_id: str, access: assistant.RunAccess, user_db: AsyncSession | None,
    *, include_route_token: bool = True,
) -> dict[str, object]:
    assistant.require_access(access)
    if access.user_id is None:
        row = await run_in_threadpool(_read_anonymous, run_id, access)
    else:
        assert user_db is not None
        try:
            row = (await user_db.execute(text(_STATUS), {"run_id": run_id})).mappings().one_or_none()
        except (SQLAlchemyError, ValueError):
            raise assistant.unavailable() from None
        if row is None:
            if await run_in_threadpool(_has_run, run_id):
                raise assistant.forbidden()
            raise assistant.not_found()

    route_id = row["route_request_id"]
    token = await run_in_threadpool(_route_access_token, route_id) if route_id and include_route_token else None
    return assistant.run_payload(row, token)
