"""Live A06 events. Postgres notifications carry only progress and wakeup signals."""

import json
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import datetime

import psycopg
from fastapi import APIRouter
from psycopg import sql
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from api.deps import AuthenticatedSession
from api.errors import ApiError
from api.repositories import assistant as store
from api.routers.assistant.chatbot import Access, RunId
from api.services import assistant, mock_assistant
from shared.config import load_db_settings
from shared.db.session import user_db_session

router = APIRouter()
_KEEPALIVE_SECONDS = 15


def _event(kind: str, **payload: object) -> str:
    data = json.dumps({"type": kind, **payload}, ensure_ascii=False)
    return f"event: {kind}\ndata: {data}\n\n"


async def _terminal(snapshot: dict, *, live: bool) -> AsyncIterator[str]:
    if snapshot["run_status"] == "failed":
        yield _event("failed", code=snapshot["error"]["code"])
    elif snapshot["run_status"] == "succeeded":
        if live and snapshot["answer"]:
            yield _event("token", text=snapshot["answer"])
        yield _event("done")


async def _mock_events(run_id: str, access: Access, initial: dict) -> AsyncIterator[str]:
    if initial["run_status"] in assistant.TERMINAL:
        async for event in _terminal(initial, live=False):
            yield event
        return
    yield _event("step", node="supervisor")
    try:
        result = await run_in_threadpool(mock_assistant.get_run, run_id, access)
    except ApiError:
        return
    yield _event("step", node="festival")
    async for event in _terminal(result, live=True):
        yield event


async def _listen_connection():
    settings = load_db_settings()
    username, password = settings.credentials("service")
    return await psycopg.AsyncConnection.connect(
        host=settings.host, port=settings.port, dbname=settings.name, user=username, password=password,
        connect_timeout=3, autocommit=True,
    )


async def _snapshot(run_id: str, access: Access) -> dict:
    if access.user_id is None:
        return await store.read(run_id, access, None, include_route_token=False)
    async with user_db_session(user_id=access.user_id) as db:
        return await store.read(run_id, access, db, include_route_token=False)


async def _postgres_events(run_id: str, access: Access, initial: dict) -> AsyncIterator[str]:
    if initial["run_status"] in assistant.TERMINAL:
        async for event in _terminal(initial, live=False):
            yield event
        return
    expires_at = None
    if access.user_id is None:
        expires_at = datetime.fromisoformat(initial["queued_at"]) + assistant.TOKEN_TTL
    try:
        async with await _listen_connection() as connection:
            await connection.execute(sql.SQL("LISTEN {}").format(sql.Identifier(assistant.notify_channel(run_id))))
            # After LISTEN commits, check for completion between authorization and subscription.
            result = await _snapshot(run_id, access)
            yield ": connected\n\n"
            while result["run_status"] not in assistant.TERMINAL:
                wait = _KEEPALIVE_SECONDS
                if expires_at is not None:
                    wait = min(wait, (expires_at - assistant.now()).total_seconds())
                    if wait <= 0:
                        return
                received_step = received_terminal = False
                async with aclosing(connection.notifies(timeout=wait, stop_after=1)) as notifications:
                    # A single database packet can contain several notifications.
                    async for signal in notifications:
                        if expires_at is not None and assistant.now() >= expires_at:
                            return
                        if signal.payload in assistant.NODES:
                            received_step = True
                            yield _event("step", node=signal.payload)
                        elif signal.payload == "terminal":
                            received_terminal = True
                if received_terminal or not received_step:
                    result = await _snapshot(run_id, access)
                if not received_step and result["run_status"] not in assistant.TERMINAL:
                    yield ": keepalive\n\n"
            async for event in _terminal(result, live=True):
                yield event
    except (ApiError, psycopg.Error, SQLAlchemyError, OSError, ValueError):
        # A transport interruption is recovered via the status endpoint.
        return


@router.get(
    "/assistant/runs/{run_id}/events", response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {}}}},
)
async def stream_run(run_id: RunId, access: Access, auth: AuthenticatedSession) -> StreamingResponse:
    if assistant.uses_assistant_db():
        initial = await store.read(run_id, access, auth[1] if auth else None, include_route_token=False)
        events = _postgres_events(run_id, access, initial)
    else:
        initial = await run_in_threadpool(mock_assistant.get_run, run_id, access)
        events = _mock_events(run_id, access, initial)
    return StreamingResponse(events, media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})
