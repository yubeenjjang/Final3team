"""W14 공통 도구 실행기: 허용 목록, 추적 ID, 귀가 재시도 문맥을 관리합니다."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


FESTIVAL_TOOLS = frozenset({"search_festivals", "get_festival", "get_crowd"})
ROUTE_TOOLS = frozenset({"get_festival", "request_return_route", "get_route_request_status"})
_STATUSES = frozenset({"upcoming", "ongoing", "ended", "cancelled"})
Transport = Callable[[Request, float], tuple[int, Mapping[str, str], Any]]


def _http_transport(request: Request, timeout_s: float) -> tuple[int, Mapping[str, str], Any]:
    try:
        with urlopen(request, timeout=timeout_s) as response:
            try:
                body = json.load(response)
            except ValueError:
                body = None
            return response.status, response.headers, body
    except HTTPError as error:
        try:
            body = json.load(error)
        except (ValueError, OSError):
            body = {}
        return error.code, error.headers, body


class ToolExecutor:
    """대화 실행마다 하나씩 생성합니다. 토큰과 멱등 키는 이 객체 안에만 보관합니다."""

    def __init__(
        self,
        base_url: str,
        allowed_tools: frozenset[str],
        *,
        timeout_s: float = 5.0,
        transport: Transport = _http_transport,
    ) -> None:
        if allowed_tools not in (FESTIVAL_TOOLS, ROUTE_TOOLS):
            raise ValueError("알 수 없는 에이전트 도구 권한입니다")
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("API 주소는 http 또는 https여야 합니다")
        self.base_url = base_url.rstrip("/")
        self.allowed_tools = allowed_tools
        self.timeout_s = timeout_s
        self.transport = transport
        self._route_tokens: dict[str, str] = {}
        self._operation_keys: dict[str, str] = {}
        self._operation_bodies: dict[str, str] = {}

    def execute(
        self,
        name: str,
        args: Mapping[str, Any],
        *,
        trace_id: str | None = None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        # 에이전트가 임의 도구를 고르더라도 서버 실행 단계에서 다시 막습니다.
        if name not in self.allowed_tools:
            return self._failure("TOOL_NOT_ALLOWED", "허용되지 않은 도구입니다")
        if trace_id is not None and (not trace_id.startswith("req_") or "\r" in trace_id or "\n" in trace_id):
            return self._failure("VALIDATION_ERROR", "추적 ID가 올바르지 않습니다")

        headers = {"Accept": "application/json"}
        if trace_id:
            headers["X-Request-ID"] = trace_id
        method, path, payload = "GET", "", None

        if name == "search_festivals":
            if set(args) - {"region", "date_from", "date_to", "q", "status", "page_size"}:
                return self._failure("VALIDATION_ERROR", "축제 검색 인자가 올바르지 않습니다")
            status = args.get("status")
            if status is not None and (
                not isinstance(status, str) or not status or
                any(part not in _STATUSES for part in status.split(","))
            ):
                return self._failure("VALIDATION_ERROR", "축제 상태값이 올바르지 않습니다")
            path = "/festivals?" + urlencode({"page_size": 10, **args})
        elif name in {"get_festival", "get_crowd"}:
            festival_id = args.get("festival_id")
            if set(args) != {"festival_id"} or not isinstance(festival_id, str) or not festival_id:
                return self._failure("VALIDATION_ERROR", "축제 ID가 필요합니다")
            path = "/festivals/" + quote(festival_id, safe="")
            if name == "get_crowd":
                path += "/crowd"
        elif name == "request_return_route":
            if not isinstance(operation_id, str) or not operation_id:
                return self._failure("VALIDATION_ERROR", "재시도에 사용할 작업 ID가 필요합니다")
            if set(args) - {"festival_id", "destination", "origin", "travel_mode", "route_preference", "user_constraints", "departure"}:
                return self._failure("VALIDATION_ERROR", "귀가 요청 인자가 올바르지 않습니다")
            if not isinstance(args.get("festival_id"), str) or not isinstance(args.get("destination"), dict):
                return self._failure("VALIDATION_ERROR", "축제와 목적지가 필요합니다")
            # 같은 작업의 재시도는 동일 본문이어야 하며, 다른 목적지는 새 작업으로 취급합니다.
            try:
                body_key = json.dumps(args, ensure_ascii=False, sort_keys=True)
            except (TypeError, ValueError):
                return self._failure("VALIDATION_ERROR", "귀가 요청 인자가 JSON 형식이 아닙니다")
            previous_body = self._operation_bodies.setdefault(operation_id, body_key)
            if previous_body != body_key:
                return self._failure("IDEMPOTENCY_CONFLICT", "같은 작업 ID에 다른 귀가 요청을 보낼 수 없습니다")
            key = self._operation_keys.setdefault(operation_id, str(uuid4()))
            payload = {**args, "request_id": key}
            method, path = "POST", "/routes/return"
            headers["Content-Type"] = "application/json"
        elif name == "get_route_request_status":
            route_id = args.get("route_request_id")
            if set(args) != {"route_request_id"} or not isinstance(route_id, str) or not route_id:
                return self._failure("VALIDATION_ERROR", "경로 요청 ID가 필요합니다")
            token = self._route_tokens.get(route_id)
            if not token:
                return self._failure("FORBIDDEN", "이 대화에서 발급한 경로 토큰이 없습니다")
            headers["X-Route-Access-Token"] = token
            path = "/routes/return/" + quote(route_id, safe="")

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            status_code, response_headers, body = self.transport(request, self.timeout_s)
        except (OSError, TimeoutError, URLError):
            return self._failure("TOOL_TIMEOUT", "도구 연결 시간이 초과됐습니다", retryable=True)
        response_id = response_headers.get("X-Request-ID") or trace_id
        if not isinstance(body, dict):
            return self._failure("TOOL_INVALID_RESPONSE", "도구 응답 형식이 올바르지 않습니다", response_id)
        if status_code >= 400:
            error = body.get("error") or {}
            if not isinstance(error, dict):
                error = {}
            return self._failure(
                str(error.get("code") or "TOOL_HTTP_ERROR"),
                str(error.get("message") or "도구 호출에 실패했습니다"),
                response_id,
                bool(error.get("retryable", status_code >= 500)),
            )
        if name == "request_return_route":
            route_id, token = body.get("route_request_id"), body.get("route_access_token")
            if isinstance(route_id, str) and isinstance(token, str):
                self._route_tokens[route_id] = token
        if name in {"request_return_route", "get_route_request_status"}:
            # 토큰과 공급원 경로 본문은 장기 보관되는 에이전트 출력으로 넘기지 않습니다.
            body = {key: value for key, value in body.items()
                    if key not in {"route_access_token", "route_candidates"}}
        return {
            "ok": True, "data": body, "request_id": response_id,
            "is_mock": body.get("is_mock") is True or response_headers.get("X-Mock") == "true",
        }

    @staticmethod
    def _failure(code: str, message: str, request_id: str | None = None, retryable: bool = False) -> dict[str, Any]:
        return {"ok": False, "error": {"code": code, "message": message, "retryable": retryable}, "request_id": request_id}
