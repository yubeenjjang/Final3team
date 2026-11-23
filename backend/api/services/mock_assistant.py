import json
import secrets
import string
from datetime import datetime, timedelta, timezone

from api.errors import ApiError
from api.mocks.store import (
    AssistantRun,
    assistant_conversations,
    assistant_lock,
    assistant_request_keys,
    assistant_runs,
)
from api.schemas.assistant import AssistantRequest
from api.services.mock_routes import create_ready_route

_ALPHABET = string.ascii_letters + string.digits
_KST = timezone(timedelta(hours=9))
_RUNS_PATH = "/api/v1/assistant/runs"


def _now() -> str:
    return datetime.now(_KST).isoformat()


def _unique_id(prefix: str, existing: set[str] | dict[str, AssistantRun]) -> str:
    while True:
        candidate = prefix + "".join(secrets.choice(_ALPHABET) for _ in range(16))
        if candidate not in existing:
            return candidate


def create_run(request: AssistantRequest, body: object) -> dict[str, object]:
    submitted_body = json.dumps(body, sort_keys=True)
    with assistant_lock:
        existing_id = assistant_request_keys.get(request.request_id)
        if existing_id is not None:
            existing = assistant_runs[existing_id]
            if existing.body != submitted_body:
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")
            return _accepted(existing)

        conversation_id = request.conversation_id
        if conversation_id is not None and conversation_id not in assistant_conversations:
            raise ApiError(403, "FORBIDDEN", "이 대화에 접근할 수 없어요.")
        if conversation_id is None:
            conversation_id = _unique_id("cv_", assistant_conversations)
            assistant_conversations.add(conversation_id)

        run_id = _unique_id("run_", assistant_runs)
        record = AssistantRun(
            run_id=run_id,
            conversation_id=conversation_id,
            access_token="rat_" + "".join(secrets.choice(_ALPHABET) for _ in range(24)),
            request=request,
            body=submitted_body,
            queued_at=_now(),
        )
        assistant_request_keys[request.request_id] = run_id
        assistant_runs[run_id] = record
        return _accepted(record)


def _accepted(run: AssistantRun) -> dict[str, object]:
    status_url = f"{_RUNS_PATH}/{run.run_id}"
    return {
        "run_id": run.run_id,
        "conversation_id": run.conversation_id,
        "run_status": "queued",
        "status_url": status_url,
        "events_url": f"{status_url}/events",
        "run_access_token": run.access_token,
        "retry_after_s": 1,
        "is_mock": True,
    }


def get_run(run_id: str, token: str | None) -> dict[str, object]:
    if not token:
        raise ApiError(401, "UNAUTHORIZED", "챗봇 작업 조회 토큰을 보내 주세요.")
    with assistant_lock:
        run = assistant_runs.get(run_id)
        if run is None:
            raise ApiError(404, "RUN_NOT_FOUND", "챗봇 작업을 찾을 수 없어요.")
        if not secrets.compare_digest(token.encode(), run.access_token.encode()):
            raise ApiError(403, "FORBIDDEN", "이 챗봇 작업을 조회할 수 없는 토큰입니다.")
        if run.started_at is None:
            run.started_at = _now()
        elif run.outcome is None:
            run.outcome = _complete_run(run.request)
            run.ended_at = _now()
        return {
            "run_id": run.run_id,
            "conversation_id": run.conversation_id,
            "run_status": "running",
            "run_kind": "chat",
            "answer": None,
            "used_tools": [],
            "evidence": [],
            "result": None,
            "route_request_id": None,
            "route_access_token": None,
            "error": None,
            "queued_at": run.queued_at,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "is_mock": True,
            **(run.outcome or {}),
        }


def _failed(tool_error: str) -> dict[str, object]:
    return {
        "run_status": "failed",
        "error": {
            "code": "AI_AGENT_FAILED",
            "message": "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요.",
            "retryable": True,
        },
        "used_tools": [{"tool": "request_return_route", "ok": False, "error_code": tool_error}],
    }


def _complete_run(request: AssistantRequest) -> dict[str, object]:
    if "실패" in request.message:
        return _failed("TOOL_TIMEOUT")
    if any(keyword in request.message for keyword in ("귀가", "돌아가", "가는 길")):
        return _complete_route_run(request.context.festival_id or "fst_000001")
    return {
        "run_status": "succeeded",
        "answer": "이번 주 서울에서 열리는 축제는 광화문 겨울빛 축제예요.(모의)",
        "used_tools": [{"tool": "search_festivals", "ok": True, "error_code": None}],
        "evidence": [{"type": "festival", "ref": "fst_000001", "provider": "tourapi", "queried_at": _now()}],
    }


def _complete_route_run(festival_id: str) -> dict[str, object]:
    try:
        route_id, route_token = create_ready_route(festival_id, "서울역")
    except ApiError as error:
        # 형식이 맞는 축제 ID도 경로를 만들 수 없는 경우가 있다.
        return _failed(error.code)
    return {
        "run_status": "succeeded",
        "answer": "경로를 찾았어요. 귀가 화면에서 확인하세요.",
        "route_request_id": route_id,
        "route_access_token": route_token,
        "evidence": [{"type": "route", "ref": route_id, "provider": "mock_adapter", "queried_at": _now()}],
        "used_tools": [
            {"tool": "get_festival", "ok": True, "error_code": None},
            {"tool": "request_return_route", "ok": True, "error_code": None},
        ],
    }
