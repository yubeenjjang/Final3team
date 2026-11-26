import secrets
import string
from datetime import datetime

from api.errors import ApiError
from api.mocks.store import (
    AssistantRun,
    assistant_conversations,
    assistant_lock,
    assistant_request_keys,
    assistant_runs,
)
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.assistant import AssistantRequest
from api.schemas.festivals import FestivalQuery
from api.services import assistant, festival_store
from api.services.festival_lookup import find_festival
from api.services.mock_routes import create_ready_route, verify_return_route_token
from ulid import ULID

_ALPHABET = string.ascii_letters + string.digits
_MOCK_FESTIVAL_ID = "fst_000001"


def _now() -> str:
    return assistant.now().astimezone(assistant.KST).isoformat()


def _unique_id(prefix: str, existing: set[str] | dict[str, AssistantRun]) -> str:
    while True:
        candidate = prefix + str(ULID())
        if candidate not in existing:
            return candidate


def create_run(
    request: AssistantRequest, body: object, access: assistant.RunAccess,
) -> dict[str, object]:
    submitted_body = assistant.digest(assistant.canonical_body(body))
    with assistant_lock:
        existing_id = assistant_request_keys.get(request.request_id)
        if existing_id is not None:
            existing = assistant_runs[existing_id]
            assistant.authorize_replay(
                existing.user_id, existing.anonymous_session_hash, assistant.digest(existing.access_token),
                datetime.fromisoformat(existing.queued_at), access,
            )
            if existing.body != submitted_body:
                raise assistant.conflict()
            # Keep the mock submission response stable for the demonstration.
            return _accepted(existing)

        conversation_id = request.conversation_id
        if conversation_id is not None:
            for previous in assistant_runs.values():
                if previous.conversation_id != conversation_id:
                    continue
                if access.user_id is not None and previous.user_id == access.user_id:
                    break
                if previous.user_id is None and assistant.matches(assistant.digest(previous.access_token), access.token_hash):
                    assistant.authorize_run(None, assistant.digest(previous.access_token),
                                            datetime.fromisoformat(previous.queued_at), access)
                    break
            else:
                raise assistant.forbidden()
        if request.context.route_request_id is not None:
            verify_return_route_token(request.context.route_request_id, access.route_token)
        if conversation_id is None:
            conversation_id = _unique_id("cv_", assistant_conversations)
            assistant_conversations.add(conversation_id)

        run_id = _unique_id("run_", assistant_runs)
        record = AssistantRun(
            run_id=run_id,
            conversation_id=conversation_id,
            access_token="rat_" + "".join(secrets.choice(_ALPHABET) for _ in range(24)),
            request=request.model_copy(update={"message": assistant.mask_private_text(request.message)}),
            body=submitted_body,
            queued_at=_now(),
            user_id=access.user_id,
            anonymous_session_hash=access.session_hash,
        )
        assistant_request_keys[request.request_id] = run_id
        assistant_runs[run_id] = record
        return _accepted(record)


def _accepted(run: AssistantRun) -> dict[str, object]:
    return assistant.accepted(run.run_id, run.conversation_id, "queued", run.access_token, True)


async def get_run(run_id: str, access: assistant.RunAccess) -> dict[str, object]:
    assistant.require_access(access)
    with assistant_lock:
        run = assistant_runs.get(run_id)
        if run is None:
            raise assistant.not_found()
    async with run.progress_lock:
        assistant.authorize_run(run.user_id, assistant.digest(run.access_token), datetime.fromisoformat(run.queued_at), access)
        if run.started_at is None:
            run.started_at = _now()
        elif run.outcome is None:
            run.outcome = await complete_run(run.request)
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
        "error": assistant.failure(),
        "used_tools": [{"tool": "request_return_route", "ok": False, "error_code": tool_error}],
    }


async def complete_run(request: AssistantRequest, *, in_process_routes: bool = True) -> dict[str, object]:
    if "실패" in request.message:
        return _failed("TOOL_TIMEOUT")
    wants_route = any(keyword in request.message for keyword in ("귀가", "돌아가", "가는 길"))
    if wants_route and not in_process_routes:
        route_id = request.context.route_request_id
        return {
            "run_status": "succeeded",
            "answer": assistant.ROUTE_ANSWER if route_id else "귀가 화면에서 경로를 요청해 주세요.(모의)",
            "route_request_id": route_id,
        }
    db_mode = uses_festival_db()
    festival_id = request.context.festival_id
    if festival_id is None and db_mode:
        page = await festival_store.list_festivals(FestivalQuery(status="ongoing", page_size=1))
        festival_id = page.items[0].festival_id if page.items else None
    elif not db_mode:
        festival_id = festival_id if wants_route and festival_id else _MOCK_FESTIVAL_ID
    if wants_route and festival_id is not None:
        return await _complete_route_run(festival_id)

    festival = await find_festival(festival_id) if festival_id is not None else None
    answer = "현재 안내할 수 있는 축제가 없어요.(모의)"
    evidence: list[dict[str, str]] = []
    if festival is not None:
        answer = (
            f"안내할 축제는 {festival.name}예요.(모의)" if db_mode
            else f"이번 주 서울에서 열리는 축제는 {festival.name}예요.(모의)"
        )
        evidence.append({
            "type": "festival", "ref": festival.festival_id, "provider": "tourapi", "queried_at": _now()
        })
    return {
        "run_status": "succeeded",
        "answer": answer,
        "used_tools": [{"tool": "search_festivals", "ok": True, "error_code": None}],
        "evidence": evidence,
    }


async def _complete_route_run(festival_id: str) -> dict[str, object]:
    try:
        route_id, route_token = await create_ready_route(festival_id, "서울역")
    except ApiError as error:
        # 형식이 맞는 축제 ID도 경로를 만들 수 없는 경우가 있다.
        return _failed(error.code)
    return {
        "run_status": "succeeded",
        "answer": assistant.ROUTE_ANSWER,
        "route_request_id": route_id,
        "route_access_token": route_token,
        "evidence": [{"type": "route", "ref": route_id, "provider": "mock_adapter", "queried_at": _now()}],
        "used_tools": [
            {"tool": "get_festival", "ok": True, "error_code": None},
            {"tool": "request_return_route", "ok": True, "error_code": None},
        ],
    }
