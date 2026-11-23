"""Model-independent single Festival Agent flow.

The caller resolves intent and slots; natural-language interpretation is a later
integration step. This module never calls Route or administrative tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


ToolCall = Callable[[str, Mapping[str, Any]], Mapping[str, Any]]
ALLOWED_TOOLS = frozenset({"search_festivals", "get_festival", "get_crowd", "get_official_notices"})


@dataclass(frozen=True)
class FestivalRequest:
    intent: str
    select_first: bool = False
    festival_id: str | None = None
    region: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    q: str | None = None
    status: str | None = None
    page_size: int | None = None
    notice_type: str | None = None


@dataclass
class FestivalResult:
    outcome: str
    answer: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)
    used_tools: list[dict[str, Any]] = field(default_factory=list)
    handoff_target: str | None = None


class FestivalAgent:
    def __init__(self, call_tool: ToolCall):
        self.call_tool = call_tool

    def run(self, request: FestivalRequest) -> FestivalResult:
        trace = ["START", "interpret"]
        if request.intent not in {"search", "detail", "crowd", "notices"}:
            target = "Route" if request.intent == "route" else "Supervisor"
            return FestivalResult("handoff_required", "담당 기능으로 전달이 필요합니다.", transitions=trace + ["handoff_required", "END"], handoff_target=target)

        trace.append("check_slots")
        if request.intent in {"detail", "crowd", "notices"} and not request.festival_id:
            return FestivalResult("clarification_needed", "어느 축제인지 알려주세요.", transitions=trace + ["clarification_needed", "END"])

        if request.intent == "search":
            tool = "search_festivals"
            args = {key: value for key in ("region", "date_from", "date_to", "q", "status", "page_size")
                    if (value := getattr(request, key)) is not None}
        elif request.intent == "notices":
            tool = "get_official_notices"
            args = {"festival_id": request.festival_id}
            if request.notice_type is not None:
                args["type"] = request.notice_type
        else:
            tool = "get_festival" if request.intent == "detail" else "get_crowd"
            args = {"festival_id": request.festival_id}
        trace.append("select_tool")
        assert tool in ALLOWED_TOOLS

        used: list[dict[str, Any]] = []
        for attempt in (1, 2):
            trace.append("call_tool")
            try:
                result = dict(self.call_tool(tool, args))
            except (OSError, TimeoutError):
                result = {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
            error = result.get("error") or {}
            used.append({"tool": tool, "ok": result.get("ok") is True, "error_code": error.get("code")})
            if result.get("ok") is True:
                break
            if not error.get("retryable") or attempt == 2:
                trace.append("handle_error")
                return self._error(error, trace, used)
            trace.append("retry_once")

        return self.validate(request, result, trace, used)

    def validate(self, request: FestivalRequest, result: Mapping[str, Any], trace: list[str], used: list[dict[str, Any]]) -> FestivalResult:
        """Validate a successful tool result; shared by direct and LangGraph runs."""
        trace.append("validate_result")
        data = result.get("data")
        if not isinstance(data, dict):
            return self._end("unavailable", "정보를 확인할 수 없습니다.", trace, used)
        mock = " (모의 데이터)" if result.get("is_mock") or data.get("is_mock") else ""

        if request.intent == "search":
            items = data.get("items")
            if not isinstance(items, list):
                return self._end("unavailable", "축제 목록을 확인할 수 없습니다.", trace, used)
            if not items:
                return self._end("answered", "조건에 맞는 축제가 없습니다." + mock, trace + ["empty_result"], used)
            evidence = [self._evidence(item) for item in items if isinstance(item, dict)]
            if len(evidence) != len(items) or any(not all(e.values()) for e in evidence):
                return self._end("unavailable", "축제 정보의 출처나 시각을 확인할 수 없습니다.", trace, used)
            names = ", ".join(
                f"{item.get('name') or item['festival_id']} (출처 {item['source']}, 갱신 {item['last_synced_at']})"
                for item in items
            )
            return self._end("answered", f"검색된 축제: {names}.{mock}", trace + ["answer"], used, evidence)

        if data.get("festival_id") != request.festival_id:
            return self._end("unavailable", "선택한 축제와 조회 결과가 일치하지 않습니다.", trace, used)
        if request.intent == "notices":
            status = data.get("status")
            if status == "unsupported":
                return self._end("unsupported", "이 축제의 공식 공지 조회는 지원하지 않습니다." + mock, trace + ["unsupported"], used)
            if status not in {"ok", "stale"}:
                return self._end("unavailable", "현재 공식 공지를 확인할 수 없습니다." + mock, trace + ["unavailable"], used)
            coverage = data.get("coverage")
            if not isinstance(coverage, dict) or coverage.get("supported") is not True:
                return self._end("unavailable", "공식 공지의 지원 범위를 확인할 수 없습니다.", trace, used)
            items = data.get("items")
            if not isinstance(items, list):
                return self._end("unavailable", "공식 공지 목록을 확인할 수 없습니다.", trace, used)
            if not items:
                return self._end("answered", "확인할 수 있는 공식 공지가 없습니다." + mock, trace + ["empty_result"], used)
            required = ("notice_id", "title", "source", "published_at", "effective_from", "effective_to")
            if any(not isinstance(item, dict) or not all(item.get(key) for key in required) for item in items):
                return self._end("unavailable", "공식 공지의 출처나 효력 시각을 확인할 수 없습니다.", trace, used)
            prefix = "오래된 자료입니다. " if status == "stale" else ""
            summaries = ", ".join(f"{item['title']} (출처 {item['source']}, 게시 {item['published_at']}, 효력 {item['effective_from']}~{item['effective_to']})" for item in items)
            evidence = [{key: item[key] for key in required} for item in items]
            return self._end("answered", f"{prefix}공식 공지: {summaries}.{mock}", trace + ["stale" if status == "stale" else "answer"], used, evidence)
        if request.intent == "detail":
            evidence = self._evidence(data)
            if not all(evidence.values()):
                return self._end("unavailable", "축제 정보의 출처나 시각을 확인할 수 없습니다.", trace, used)
            venue = data.get("venue_name") or "장소 미확인"
            answer = f"{data.get('name') or request.festival_id}: {venue}. 출처 {evidence['source']}, 자료 갱신 {evidence['last_synced_at']}.{mock}"
            return self._end("answered", answer, trace + ["answer"], used, [evidence])

        status = data.get("status")
        if status == "unsupported":
            return self._end("unsupported", "이 축제 주변 지역의 혼잡 정보는 지원하지 않습니다." + mock, trace + ["unsupported"], used)
        if status == "unavailable":
            return self._end("unavailable", "현재 혼잡 정보를 확인할 수 없습니다." + mock, trace + ["unavailable"], used)
        if status not in {"ok", "stale"}:
            return self._end("unavailable", "혼잡 정보의 상태를 확인할 수 없습니다.", trace, used)
        coverage = data.get("coverage")
        if not isinstance(coverage, dict) or coverage.get("supported") is not True:
            return self._end("unavailable", "혼잡 정보의 지원 범위를 확인할 수 없습니다.", trace, used)
        areas = data.get("areas")
        if not isinstance(areas, list) or not areas or not isinstance(areas[0], dict):
            return self._end("unavailable", "확인된 혼잡 구역 정보가 없습니다.", trace, used)
        area = areas[0]
        observed_at = area.get("observed_at") or data.get("observed_at")
        if not (area.get("area_name") and area.get("congest_level") and observed_at):
            return self._end("unavailable", "혼잡 자료의 구역·시각·수준을 확인할 수 없습니다.", trace, used)
        prefix = "오래된 자료입니다. " if status == "stale" else ""
        answer = f"{prefix}{area['area_name']} 지역 혼잡은 {area['congest_level']}입니다. 관측 시각 {observed_at}. 행사장 내부나 이동 경로의 혼잡을 뜻하지 않습니다.{mock}"
        evidence = [{"festival_id": request.festival_id, "area_name": area["area_name"], "observed_at": observed_at, "status": status, "coverage": coverage}]
        return self._end("answered", answer, trace + ["stale" if status == "stale" else "answer"], used, evidence)

    @staticmethod
    def _evidence(item: Mapping[str, Any]) -> dict[str, Any]:
        return {"festival_id": item.get("festival_id"), "source": item.get("source"), "last_synced_at": item.get("last_synced_at")}

    @staticmethod
    def _end(outcome: str, answer: str, trace: list[str], used: list[dict[str, Any]], evidence: list[dict[str, Any]] | None = None) -> FestivalResult:
        return FestivalResult(outcome, answer, evidence or [], trace + ["END"], used)

    def _error(self, error: Mapping[str, Any], trace: list[str], used: list[dict[str, Any]]) -> FestivalResult:
        code = error.get("code")
        if code == "FESTIVAL_NOT_FOUND":
            return self._end("clarification_needed", "해당 축제를 찾지 못했습니다. 다시 선택해 주세요.", trace + ["clarification_needed"], used)
        if code == "VALIDATION_ERROR":
            return self._end("clarification_needed", "검색 조건을 다시 확인해 주세요.", trace + ["clarification_needed"], used)
        return self._end("unavailable", "정보를 확인할 수 없습니다.", trace + ["unavailable"], used)
