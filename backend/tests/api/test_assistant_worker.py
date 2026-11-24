import asyncio
import time
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.jobs import assistant_runner, assistant_worker
from api.jobs.assistant_queue import Claim
from api.jobs.assistant_runner import AgentResult, RunInput, get_runner, is_transient
from api.realtime import job_events
from api.schemas.assistant import AssistantRequest
from api.services import assistant

QUERY = "/api/v1/assistant/query"


def submit(client, **body):
    return client.post(QUERY, json={"request_id": f"test-{uuid4()}", "message": "축제 안내", **body})


def run_headers(run):
    return {"X-Run-Access-Token": run["run_access_token"]}


def test_mock_sse_authorizes_before_streaming_and_closes(client):
    run = submit(client).json()
    assert client.get(run["events_url"]).status_code == 401
    assert client.get(run["events_url"], headers={"X-Run-Access-Token": "other"}).status_code == 403
    response = client.get(run["events_url"], headers=run_headers(run))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "private, no-store"
    assert "event: step" in response.text
    assert "event: token" in response.text
    assert response.text.endswith('event: done\ndata: {"type": "done"}\n\n')
    completed = client.get(run["events_url"], headers=run_headers(run))
    assert completed.text == 'event: done\ndata: {"type": "done"}\n\n'

    failed = submit(client, message="실패").json()
    response = client.get(failed["events_url"], headers=run_headers(failed))
    assert response.status_code == 200
    assert response.text.endswith('event: failed\ndata: {"type": "failed", "code": "AI_AGENT_FAILED"}\n\n')


def test_anonymous_continuation_and_replay_require_ownership(client, monkeypatch):
    body = {"request_id": "owner-001", "message": "질문"}
    run = client.post(QUERY, json=body).json()
    with TestClient(client.app) as outsider:
        assert outsider.post(QUERY, json=body).status_code == 403
        assert submit(outsider, conversation_id=run["conversation_id"]).status_code == 403
        assert outsider.post(QUERY, json=body, headers=run_headers(run)).json() == run
    assert submit(client, conversation_id=run["conversation_id"]).status_code == 403
    assert submit(client, context={"route_request_id": "rr_zzzzzz"}).status_code == 403
    created_at = assistant.now()
    monkeypatch.setattr(assistant, "now", lambda: created_at + timedelta(minutes=11))
    assert client.get(run["status_url"], headers=run_headers(run)).status_code == 401
    assert client.get(run["events_url"], headers=run_headers(run)).status_code == 401


def test_submission_rate_limit_and_db_registration_failure(client, monkeypatch):
    monkeypatch.setenv("ASSISTANT_RATE_LIMIT_PER_MIN", "2")
    assert submit(client).status_code == 202
    assert submit(client).status_code == 202
    limited = submit(client)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) > 0
    monkeypatch.setenv("ASSISTANT_RATE_LIMIT_PER_MIN", "10")
    monkeypatch.setenv("ASSISTANT_PROVIDER", "db")
    monkeypatch.delenv("ASSISTANT_TOKEN_SECRET", raising=False)
    unavailable = submit(client)
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "AI_AGENT_FAILED"
    assert "X-Mock" not in unavailable.headers


def test_question_and_header_values_are_absent_from_logs(client, caplog):
    private = "010-1234-5678, 서울특별시 중구 세종대로 110, user@example.test"
    with caplog.at_level("INFO", logger="uvicorn.error.api_requests"):
        response = client.post(QUERY, headers={"X-Request-ID": private[-42:].encode("utf-8").hex()[:64]},
                               json={"request_id": "privacy-001", "message": private})
        run = response.json()
        result = client.get(run["events_url"], headers=run_headers(run))
    assert result.status_code == 200
    assert private not in caplog.text
    assert "광화문 겨울빛 축제" not in caplog.text
    assert response.headers["X-Request-ID"] not in caplog.text
    assert run["run_access_token"] not in caplog.text
    assert assistant.mask_private_text(private) == "[연락처], [주소], [연락처]"


def test_default_fallback_and_configured_festival_runner(monkeypatch):
    monkeypatch.delenv("ASSISTANT_FESTIVAL_RUNNER", raising=False)
    def missing(module):
        raise ModuleNotFoundError(name=module)

    monkeypatch.setattr(assistant_runner, "import_module", missing)
    job = RunInput("run_000001", AssistantRequest(request_id="runner-test", message="축제"))
    nodes = []
    result = get_runner().run(job, nodes.append)
    assert result.is_mock
    assert result.answer
    assert nodes == ["supervisor", "festival"]

    async def run(received, step):
        assert received is job
        step("festival")
        return {"answer": "실행 결과"}

    monkeypatch.setenv("ASSISTANT_FESTIVAL_RUNNER", "agents.test_festival:run")
    monkeypatch.setattr(assistant_runner, "import_module", lambda _: SimpleNamespace(run=run))
    result = get_runner().run(job, nodes.append)
    assert not result.is_mock
    assert result.answer == "실행 결과"
    assert nodes[-1] == "festival"


@dataclass
class UpstreamError(Exception):
    status_code: int


@pytest.mark.parametrize(("error", "retry"), [
    (TimeoutError(), True), (UpstreamError(429), True), (UpstreamError(503), True),
    (UpstreamError(401), False), (RuntimeError(), False),
])
def test_retry_only_transient_agent_failures(error, retry):
    assert is_transient(error) is retry


def _hang(send, claim):
    with send:
        time.sleep(10)


def _return_result(send, claim):
    with send:
        send.send((AgentResult(answer="완료"), False))


def test_attempt_process_is_hard_bounded():
    started = time.monotonic()
    result, retry = assistant_worker.run_attempt(Claim("run_000001", 1, 0.5), target=_hang)
    assert retry and result.error_code == "AI_AGENT_FAILED"
    assert time.monotonic() - started < 5
    result, retry = assistant_worker.run_attempt(Claim("run_000001", 2, 5), target=_return_result)
    assert not retry and result.answer == "완료"


def test_postgres_sse_drains_each_notification_packet(monkeypatch):
    class Listener:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def execute(self, statement):
            pass

        async def notifies(self, **_):
            for payload in ("supervisor", "festival", "terminal"):
                yield SimpleNamespace(payload=payload)

    async def connect():
        return Listener()

    queued = {"run_status": "queued"}
    done = {"run_status": "succeeded", "answer": "완료"}
    snapshots = iter((queued, done))

    async def snapshot(*_):
        return next(snapshots)

    monkeypatch.setattr(job_events, "_listen_connection", connect)
    monkeypatch.setattr(job_events, "_snapshot", snapshot)

    async def receive():
        access = assistant.RunAccess(uuid4())
        return [event async for event in job_events._postgres_events("run_000001", access, queued)]

    packets = asyncio.run(receive())
    assert len(packets) == 5
    assert '"node": "supervisor"' in packets[1]
    assert '"node": "festival"' in packets[2]
    assert "event: token" in packets[3]
    assert "event: done" in packets[4]
