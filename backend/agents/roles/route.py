"""Minimal Route Agent: interpret A04/A05 metadata without retaining route bodies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


ToolCall = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class RouteRequest:
    festival_id: str
    destination: dict[str, Any]
    travel_mode: str = "transit"
    route_preference: str = "fastest"


@dataclass
class RouteResult:
    outcome: str
    answer: str
    route_request_id: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    used_tools: list[str] = field(default_factory=list)


class RouteAgent:
    """Caller owns the per-conversation ToolExecutor, trace ID, and operation ID.

    A queued request is returned for later polling. A04 owns provider fallback.
    """

    def __init__(self, call_tool: ToolCall):
        self.call_tool = call_tool

    def request(self, request: RouteRequest) -> RouteResult:
        if not isinstance(request.festival_id, str) or not request.festival_id.strip():
            return RouteResult("clarification_needed", "어느 축제에서 출발하시는지 알려주세요.")
        if not isinstance(request.destination, dict) or not request.destination:
            return RouteResult("clarification_needed", "돌아갈 목적지를 알려주세요.")
        response = self.call_tool("request_return_route", {
            "festival_id": request.festival_id,
            "destination": request.destination,
            "travel_mode": request.travel_mode,
            "route_preference": request.route_preference,
        })
        return self._interpret(response, "request_return_route")

    def check_status(self, route_request_id: str) -> RouteResult:
        if not isinstance(route_request_id, str) or not route_request_id.strip():
            return RouteResult("clarification_needed", "조회할 경로 요청 ID가 필요합니다.")
        response = self.call_tool("get_route_request_status", {"route_request_id": route_request_id})
        return self._interpret(response, "get_route_request_status")

    @staticmethod
    def _interpret(response: Mapping[str, Any], tool_name: str) -> RouteResult:
        used = [tool_name]
        if response.get("ok") is not True:
            error = response.get("error") or {}
            code = error.get("code") if isinstance(error, Mapping) else None
            return RouteResult("unavailable", _failure_message(code),
                               evidence={"error_code": code}, used_tools=used)

        data = response.get("data")
        if not isinstance(data, Mapping):
            return RouteResult("unavailable", "경로 조회 결과를 확인할 수 없습니다.", used_tools=used)
        status = data.get("route_status")
        route_id = data.get("route_request_id")
        route_id = route_id if isinstance(route_id, str) and route_id else None
        evidence = {key: data[key] for key in (
            "route_status", "provider", "provider_tier", "queried_at", "updated_at",
            "completed_valid_route", "is_mock", "retry_after_s",
        ) if key in data}
        if status == "ready" and data.get("completed_valid_route") is True and route_id:
            provider = data.get("provider")
            queried_at = data.get("queried_at")
            source = f" 출처: {provider}." if isinstance(provider, str) and provider else " 출처는 확인되지 않았습니다."
            time = f" 조회 시각: {queried_at}." if isinstance(queried_at, str) and queried_at else " 조회 시각은 확인되지 않았습니다."
            mock = " (모의 데이터)" if data.get("is_mock") is True or response.get("is_mock") is True else ""
            return RouteResult("answered", "귀가 경로를 찾았습니다. 귀가 화면에서 확인해 주세요." + source + time + mock,
                               route_id, evidence, used)
        if status in {"queued", "processing"} and route_id:
            return RouteResult("pending", "귀가 경로를 확인하고 있습니다. 잠시 뒤 상태를 다시 확인해 주세요.",
                               route_id, evidence, used)
        error = data.get("error") or {}
        code = error.get("code") if isinstance(error, Mapping) else None
        evidence["error_code"] = code
        if status == "ready":
            return RouteResult("unavailable", "경로 완료 표시가 있지만 유효한 경로를 확인할 수 없습니다.",
                               route_id, evidence, used)
        return RouteResult("unavailable", _failure_message(code), route_id, evidence, used)


def _failure_message(code: Any) -> str:
    if code == "ROUTE_NO_RESULT":
        return "현재 이용 가능한 귀가 경로를 찾지 못했습니다."
    if code in {"ROUTE_TIMEOUT", "TOOL_TIMEOUT"}:
        return "경로 조회 시간이 초과됐습니다. 잠시 뒤 다시 확인해 주세요."
    if code in {"ROUTE_RESULT_EXPIRED", "ROUTE_ACCESS_EXPIRED"}:
        return "이전 경로 조회 결과가 만료됐습니다. 새로 조회해 주세요."
    if code == "ROUTE_OVERLOADED":
        return "요청이 몰려 경로 조회를 접수하지 못했습니다. 잠시 뒤 다시 시도해 주세요."
    return "귀가 경로를 확인할 수 없습니다. 다시 조회해 주세요."
