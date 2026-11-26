"""LangGraph nodes and branches for the first standalone Festival Agent flow."""

from __future__ import annotations

from time import monotonic
from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.roles.festival import FestivalAgent, FestivalRequest, FestivalResult, ToolCall

MAX_TOOL_CALLS = 4  # Three normal stages plus one transient retry.


class FestivalGraphState(TypedDict, total=False):
    request: FestivalRequest
    trace: list[str]
    tool: str
    args: dict[str, Any]
    response: dict[str, Any]
    attempts: int
    used_tools: list[dict[str, Any]]
    result: FestivalResult
    stage: str
    selected_festival_id: str
    parts: list[str]
    evidence: list[dict[str, Any]]
    deadline_at: float
    tool_call_count: int
    timeout_s: float


def build_festival_graph(call_tool: ToolCall, *, timeout_s: float = 30.0, clock: Callable[[], float] = monotonic):
    """Compile a bounded graph; callers provide resolved intent and slots."""
    agent = FestivalAgent(call_tool)

    def interpret(state: FestivalGraphState) -> dict[str, Any]:
        request = state["request"]
        trace = ["START", "interpret"]
        if request.intent not in {"search", "detail", "crowd", "notices", "search_detail_crowd"}:
            target = "Route" if request.intent == "route" else "Supervisor"
            result = FestivalResult("handoff_required", "담당 기능으로 전달이 필요합니다.", transitions=trace + ["handoff_required", "END"], handoff_target=target)
            return {"trace": result.transitions, "result": result}
        return {"trace": trace, "deadline_at": clock() + timeout_s, "timeout_s": timeout_s,
                "tool_call_count": 0, "used_tools": [], "parts": [], "evidence": [],
                "stage": "search" if request.intent == "search_detail_crowd" else request.intent}

    def slots(state: FestivalGraphState) -> dict[str, Any]:
        request = state["request"]
        trace = state["trace"] + ["check_slots"]
        if request.intent in {"detail", "crowd", "notices"} and not request.festival_id:
            result = FestivalResult("clarification_needed", "어느 축제인지 알려주세요.", transitions=trace + ["clarification_needed", "END"])
            return {"trace": result.transitions, "result": result}
        if request.intent == "search_detail_crowd" and not request.select_first:
            result = FestivalResult("clarification_needed", "검색 결과 중 어느 축제를 볼지 알려주세요.", transitions=trace + ["clarification_needed", "END"])
            return {"trace": result.transitions, "result": result}
        return {"trace": trace}

    def select_tool(state: FestivalGraphState) -> dict[str, Any]:
        request = state["request"]
        stage = state["stage"]
        if stage == "search":
            tool = "search_festivals"
            args = {key: value for key in ("region", "date_from", "date_to", "q", "status", "page_size")
                    if (value := getattr(request, key)) is not None}
        elif stage == "notices":
            tool = "get_official_notices"
            args = {"festival_id": state.get("selected_festival_id") or request.festival_id}
            if request.notice_type is not None:
                args["type"] = request.notice_type
        else:
            tool = "get_festival" if stage == "detail" else "get_crowd"
            args = {"festival_id": state.get("selected_festival_id") or request.festival_id}
        return {"tool": tool, "args": args, "attempts": 0, "trace": state["trace"] + ["select_tool"]}

    def invoke_tool(state: FestivalGraphState) -> dict[str, Any]:
        trace = state["trace"] + ["call_tool"]
        if clock() >= state["deadline_at"] or state["tool_call_count"] >= MAX_TOOL_CALLS:
            result = _budget_result(state, trace)
            return {"result": result, "trace": result.transitions}
        try:
            response = dict(call_tool(state["tool"], state["args"]))
        except (OSError, TimeoutError):
            response = {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
        error = response.get("error") or {}
        used = state["used_tools"] + [{"tool": state["tool"], "ok": response.get("ok") is True, "error_code": error.get("code")}]
        if clock() >= state["deadline_at"]:
            result = _budget_result({**state, "used_tools": used}, trace)
            return {"result": result, "used_tools": used, "tool_call_count": state["tool_call_count"] + 1, "trace": result.transitions}
        return {"response": response, "attempts": state["attempts"] + 1,
                "tool_call_count": state["tool_call_count"] + 1, "used_tools": used, "trace": trace}

    def after_call(state: FestivalGraphState) -> str:
        if "result" in state:
            return "done"
        response = state["response"]
        if response.get("ok") is True:
            return "validate"
        if (response.get("error") or {}).get("retryable") and state["attempts"] < 2 and state["tool_call_count"] < MAX_TOOL_CALLS:
            return "retry"
        return "error"

    def retry(state: FestivalGraphState) -> dict[str, Any]:
        return {"trace": state["trace"] + ["retry_once"]}

    def validate(state: FestivalGraphState) -> dict[str, Any]:
        request = state["request"]
        if request.intent != "search_detail_crowd":
            result = agent.validate(request, state["response"], list(state["trace"]), state["used_tools"])
            return {"result": result, "trace": result.transitions}
        stage = state["stage"]
        phase_request = FestivalRequest(stage, festival_id=state.get("selected_festival_id"),
                                        region=request.region, date_from=request.date_from,
                                        date_to=request.date_to, q=request.q, status=request.status,
                                        page_size=request.page_size)
        result = agent.validate(phase_request, state["response"], list(state["trace"]), state["used_tools"])
        if stage == "search" and result.outcome == "answered" and result.evidence:
            selected = result.evidence[0]["festival_id"]
            return {"selected_festival_id": selected, "stage": "detail", "parts": [result.answer],
                    "evidence": result.evidence, "trace": result.transitions[:-1] + ["advance_detail"]}
        if stage == "detail" and result.outcome == "answered":
            return {"stage": "crowd", "parts": state["parts"] + [result.answer],
                    "evidence": state["evidence"] + result.evidence,
                    "trace": result.transitions[:-1] + ["advance_crowd"]}
        return _finish_composite(state, result)

    def error(state: FestivalGraphState) -> dict[str, Any]:
        if ((state["response"].get("error") or {}).get("retryable")
                and state["attempts"] < 2 and state["tool_call_count"] >= MAX_TOOL_CALLS):
            result = _budget_result(state, state["trace"] + ["handle_error"])
            return {"result": result, "trace": result.transitions}
        result = agent._error(state["response"].get("error") or {}, state["trace"] + ["handle_error"], state["used_tools"])
        if state["request"].intent == "search_detail_crowd":
            return _finish_composite(state, result)
        return {"result": result, "trace": result.transitions}

    def _finish_composite(state: FestivalGraphState, phase: FestivalResult) -> dict[str, Any]:
        parts = state["parts"] + [phase.answer]
        evidence = state["evidence"] + phase.evidence
        outcome = "partial" if state["parts"] and phase.outcome != "answered" else phase.outcome
        result = FestivalResult(outcome, " ".join(parts), evidence,
                                phase.transitions, state["used_tools"])
        return {"result": result, "trace": result.transitions}

    def _budget_result(state: FestivalGraphState, trace: list[str]) -> FestivalResult:
        parts = state.get("parts") or []
        missing = "혼잡 정보를" if state.get("stage") == "crowd" else ("나머지 정보를" if parts else "요청한 정보를")
        answer = " ".join(parts + [f"조회 제한에 도달해 {missing} 확인할 수 없습니다."])
        return FestivalResult("partial" if parts else "unavailable", answer,
                              state.get("evidence") or [], trace + ["budget_exceeded", "END"],
                              state.get("used_tools") or [])

    graph = StateGraph(FestivalGraphState)
    graph.add_node("interpret", interpret)
    graph.add_node("check_slots", slots)
    graph.add_node("select_tool", select_tool)
    graph.add_node("call_tool", invoke_tool)
    graph.add_node("retry", retry)
    graph.add_node("validate", validate)
    graph.add_node("error", error)
    graph.add_edge(START, "interpret")
    graph.add_conditional_edges("interpret", lambda s: "done" if "result" in s else "slots", {"done": END, "slots": "check_slots"})
    graph.add_conditional_edges("check_slots", lambda s: "done" if "result" in s else "select", {"done": END, "select": "select_tool"})
    graph.add_edge("select_tool", "call_tool")
    graph.add_conditional_edges("call_tool", after_call, {"validate": "validate", "retry": "retry", "error": "error", "done": END})
    graph.add_edge("retry", "call_tool")
    graph.add_conditional_edges("validate", lambda s: "done" if "result" in s else "next", {"done": END, "next": "select_tool"})
    graph.add_edge("error", END)
    return graph.compile()


def run_festival_graph(call_tool: ToolCall, request: FestivalRequest, *, timeout_s: float = 30.0, clock: Callable[[], float] = monotonic) -> FestivalResult:
    state = build_festival_graph(call_tool, timeout_s=timeout_s, clock=clock).invoke({"request": request})
    return state["result"]
