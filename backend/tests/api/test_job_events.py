import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from api.auth import service, state
from api.auth.tokens import AccessClaims
from api.deps import CurrentUser
from api.errors import ApiError
from api.realtime import job_events
from api.repositories import assistant as store
from api.repositories.route_store import TOKEN_TTL
from api.services import assistant, chat


@pytest.mark.parametrize(("invalid", "payload"), [
    ("revoked", "festival"), ("disabled", "terminal"), ("expired", "terminal"), (None, "terminal"),
])
def test_logged_in_stream_checks_access_before_sending_events(monkeypatch, invalid, payload):
    clock = [datetime.now(timezone.utc).replace(microsecond=0)]
    claims = AccessClaims(uuid4(), "sse-test-session", int(clock[0].timestamp()) + 5)
    access = assistant.RunAccess(claims.user_id)
    initial = {"run_status": "running", "queued_at": (clock[0] - timedelta(hours=1)).isoformat()}
    completed = {"run_status": "succeeded", "answer": "시험 답변"}
    memory = state.MemoryAuthState()
    active = Mock(return_value=True)
    wait_times = []

    async def notifies(*, timeout, stop_after):
        wait_times.append(timeout)
        yield SimpleNamespace(payload=payload)

    @asynccontextmanager
    async def listener():
        yield SimpleNamespace(execute=AsyncMock(), notifies=notifies)

    monkeypatch.setenv("ASSISTANT_PROVIDER", "db")
    monkeypatch.setattr(assistant, "now", lambda: clock[0])
    monkeypatch.setattr(chat, "time", lambda: clock[0].timestamp())
    monkeypatch.setattr(state, "_auth_state", memory)
    monkeypatch.setattr(service, "account_is_active", active)
    monkeypatch.setattr(store, "read", AsyncMock(return_value=initial))
    monkeypatch.setattr(job_events, "_snapshot", AsyncMock(side_effect=[initial, completed]))
    monkeypatch.setattr(job_events, "_listen_connection", AsyncMock(side_effect=listener))

    async def collect():
        stream = await job_events.stream_run("run_fixture", access, (CurrentUser(claims, "user", True), None))
        events = stream.body_iterator
        assert await anext(events) == ": connected\n\n"
        if invalid == "revoked":
            memory.revoke(claims.jti, 5)
        elif invalid == "disabled":
            active.return_value = False
        elif invalid == "expired":
            clock[0] += timedelta(seconds=5)
        return [event async for event in events]

    events = asyncio.run(collect())
    assert wait_times == ([] if invalid == "expired" else [5])
    assert [event.splitlines()[0] for event in events] == ([] if invalid else ["event: token", "event: done"])


def test_revoked_session_cannot_receive_completed_replay(monkeypatch):
    now = datetime.now(timezone.utc)
    claims = AccessClaims(uuid4(), "sse-replay-session", int(now.timestamp()) + 60)
    memory = state.MemoryAuthState()
    monkeypatch.setenv("ASSISTANT_PROVIDER", "db")
    monkeypatch.setattr(state, "_auth_state", memory)
    monkeypatch.setattr(store, "read", AsyncMock(return_value={"run_status": "succeeded"}))

    async def collect():
        stream = await job_events.stream_run(
            "run_fixture", assistant.RunAccess(claims.user_id), (CurrentUser(claims, "user", True), None),
        )
        memory.revoke(claims.jti, 60)
        return [event async for event in stream.body_iterator]

    assert asyncio.run(collect()) == []


def test_expired_route_context_returns_auth_error(monkeypatch):
    now = datetime.now(timezone.utc)
    token = "fixture-route-context"
    row = SimpleNamespace(access_token_hash=assistant.digest(token), submitted_at=now - TOKEN_TTL)
    db = Mock()
    db.execute.return_value.one_or_none.return_value = row
    monkeypatch.setattr(assistant, "now", lambda: now)
    with pytest.raises(ApiError) as error:
        store._verify_route_context(db, "rr_fixture", token)
    assert (error.value.status, error.value.code) == (401, "UNAUTHORIZED")
