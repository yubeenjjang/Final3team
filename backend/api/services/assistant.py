"""A06 authorization, response formats and privacy rules shared by both providers."""

import hashlib
import hmac
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from time import monotonic
from typing import Protocol
from uuid import UUID

from api.errors import ApiError

TOKEN_TTL = timedelta(minutes=10)
KST = timezone(timedelta(hours=9))
TERMINAL = {"succeeded", "failed"}
FAILURE_CODE = "AI_AGENT_FAILED"
FAILURE_MESSAGE = "답변을 만들지 못했어요. 축제 검색과 귀가 조회는 그대로 쓸 수 있어요."
ROUTE_ANSWER = "경로를 찾았어요. 귀가 화면에서 확인하세요."
NODES = frozenset({"supervisor", "festival", "festival_agent", "route", "route_agent"})
ANONYMOUS_COOKIE = "noldaga_assistant"
_SESSION_FORMAT = re.compile(r"[A-Za-z0-9_-]{43}")

_CONTACT = re.compile(
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"
    r"|(?<!\d)(?:\+82[ .-]?)?(?:0?1[016789]|0[2-6]\d?|070|050\d?)[ .-]?\d{3,4}[ .-]?\d{4}(?!\d)"
)
_ADDRESS = re.compile(
    r"(?:[가-힣]+(?:특별시|광역시|자치시|자치도|도|시|군|구|읍|면)\s+)*"
    r"[가-힣0-9·]+(?:대로|로|길|동|리)\s*\d+(?:-\d+)?"
    r"(?:\s*(?:번지|[0-9-]+(?:동|층|호)))*"
)


def uses_assistant_db() -> bool:
    return os.environ.get("ASSISTANT_PROVIDER") == "db"


def now() -> datetime:
    return datetime.now(timezone.utc)


def mask_private_text(value: str) -> str:
    return _ADDRESS.sub("[주소]", _CONTACT.sub("[연락처]", value))


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def matches(expected: str | None, candidate: str | None) -> bool:
    return bool(expected and candidate and hmac.compare_digest(expected, candidate))


def anonymous_session(value: str | None) -> str | None:
    return value if value and _SESSION_FORMAT.fullmatch(value) else None


@dataclass(frozen=True)
class RunAccess:
    user_id: UUID | None
    run_token: str | None = field(default=None, repr=False)
    session: str | None = field(default=None, repr=False)
    route_token: str | None = field(default=None, repr=False)

    @property
    def token_hash(self) -> str | None:
        return digest(self.run_token) if self.run_token else None

    @property
    def session_hash(self) -> str | None:
        return digest(self.session) if self.session else None


def require_access(access: RunAccess) -> None:
    if access.user_id is None and not access.run_token:
        raise ApiError(401, "UNAUTHORIZED", "챗봇 작업 조회 토큰을 보내 주세요.")


def authorize_run(owner: UUID | None, token_hash: str | None, queued_at: datetime, access: RunAccess) -> None:
    if access.user_id is not None:
        if access.user_id == owner:
            return
        raise forbidden()
    if owner is not None or not matches(token_hash, access.token_hash):
        raise forbidden()
    if now() >= queued_at + TOKEN_TTL:
        raise ApiError(401, "UNAUTHORIZED", "챗봇 작업 조회 토큰이 만료됐어요.")


def authorize_replay(
    owner: UUID | None, session_hash: str | None, token_hash: str | None, queued_at: datetime, access: RunAccess,
) -> None:
    if owner is None and access.user_id is None and matches(session_hash, access.session_hash):
        return
    authorize_run(owner, token_hash, queued_at, access)


def forbidden() -> ApiError:
    return ApiError(403, "FORBIDDEN", "이 챗봇 작업 또는 대화에 접근할 수 없어요.")


def not_found() -> ApiError:
    return ApiError(404, "RUN_NOT_FOUND", "챗봇 작업을 찾을 수 없어요.")


def conflict() -> ApiError:
    return ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")


def unavailable() -> ApiError:
    return ApiError(503, FAILURE_CODE, "챗봇 작업 저장소에 연결할 수 없어요.", True)


def failure(code: str = FAILURE_CODE, retryable: bool = True) -> dict[str, object]:
    return {"code": code, "message": FAILURE_MESSAGE, "retryable": retryable}


def accepted(run_id: str, conversation_id: str, status: str, token: str, is_mock: bool) -> dict[str, object]:
    status_url = f"/api/v1/assistant/runs/{run_id}"
    return {
        "run_id": run_id, "conversation_id": conversation_id, "run_status": status,
        "status_url": status_url, "events_url": f"{status_url}/events",
        "run_access_token": token, "retry_after_s": 1, "is_mock": is_mock,
    }


def canonical_body(body: object) -> str:
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def notify_channel(run_id: str) -> str:
    return "assistant_" + run_id


def run_payload(row: Mapping, route_token: str | None = None) -> dict[str, object]:
    status = row["run_status"]
    answer = row["answer"]
    if answer:
        answer = ROUTE_ANSWER if row["route_request_id"] else mask_private_text(answer)
    return {
        "run_id": row["run_id"], "conversation_id": row["conversation_id"],
        "run_status": status, "run_kind": row["run_kind"],
        "answer": answer if status == "succeeded" else None,
        "result": row["result"] if status == "succeeded" else None,
        "used_tools": row["used_tools"], "evidence": row["evidence"] if status == "succeeded" else [],
        "route_request_id": row["route_request_id"], "route_access_token": route_token,
        "error": failure(row["error_code"], row["error_retryable"]) if status == "failed" else None,
        "queued_at": row["queued_at"].astimezone(KST).isoformat(),
        "started_at": row["started_at"].astimezone(KST).isoformat() if row["started_at"] else None,
        "ended_at": row["ended_at"].astimezone(KST).isoformat() if row["ended_at"] else None,
        "is_mock": row["is_mock"],
    }


class AssistantRateLimit(Protocol):
    def retry_after(self, keys: tuple[str, ...], limit: int) -> int | None: ...


class MemoryAssistantRateLimit:
    def __init__(self) -> None:
        self._lock = Lock()
        self._window = -1
        self._counts: dict[str, int] = {}

    def retry_after(self, keys: tuple[str, ...], limit: int) -> int | None:
        seconds = int(monotonic())
        window, elapsed = divmod(seconds, 60)
        with self._lock:
            if window != self._window:
                self._counts.clear()
                self._window = window
            if any(self._counts.get(key, 0) >= limit for key in keys):
                return 60 - elapsed
            for key in keys:
                self._counts[key] = self._counts.get(key, 0) + 1
        return None


rate_limit: AssistantRateLimit = MemoryAssistantRateLimit()


def enforce_rate_limit(ip: str, user_id: UUID | None) -> None:
    from api.auth.tokens import positive_setting

    ip_key = "ip:" + digest(ip)
    keys = (ip_key,) if user_id is None else (ip_key, f"user:{user_id}")
    retry = rate_limit.retry_after(keys, positive_setting("ASSISTANT_RATE_LIMIT_PER_MIN", 10))
    if retry is not None:
        raise ApiError(429, "RATE_LIMITED", "질문이 많아 잠시 후 다시 시도해 주세요.", True, retry_after=retry)
