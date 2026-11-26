"""Bounded Festival detail recheck prototype for W28.

The judge is injected so fixed-response tests cannot be mistaken for a live LLM
evaluation. The code still enforces the original request after the judgment.
"""

from __future__ import annotations

from datetime import date, datetime
from time import monotonic
from typing import Any, Callable, Mapping

from agents.roles.festival import FestivalAgent, FestivalRequest, FestivalResult, ToolCall


def run_reflected_detail(
    call_tool: ToolCall,
    request: FestivalRequest,
    judge: Callable[[dict[str, Any]], Mapping[str, Any]],
    *,
    as_of: date,
    clock: Callable[[], float] = monotonic,
    timeout_s: float = 30.0,
    max_calls: int = 4,
) -> tuple[FestivalResult, dict[str, Any]]:
    """Review a detail result and, if justified, search then fetch the same ID."""
    if request.intent != "detail" or not request.festival_id or not request.q or not request.region:
        raise ValueError("detail, festival_id, q and region are required")
    if max_calls < 1 or max_calls > 4 or timeout_s <= 0:
        raise ValueError("invalid W28 budget")
    deadline = clock() + timeout_s
    calls: list[dict[str, Any]] = []
    record: dict[str, Any] = {"case": "detail_evidence_recheck", "judge_used": False,
                              "first_issue": None, "judge_decision": None,
                              "tool_calls": calls, "as_of": as_of.isoformat()}

    def unavailable(reason: str) -> tuple[FestivalResult, dict[str, Any]]:
        record["final_reason"] = reason
        return FestivalResult("unavailable", "선택한 축제 정보를 확인할 수 없습니다.",
                              transitions=["START", "reflect", reason, "END"], used_tools=calls), record

    def invoke(name: str, args: dict[str, Any]) -> Mapping[str, Any] | None:
        if len(calls) >= max_calls or clock() >= deadline:
            return None
        try:
            response = call_tool(name, args)
        except (OSError, TimeoutError):
            response = {"ok": False, "error": {"code": "TOOL_TIMEOUT"}}
        calls.append({"tool": name, "args": dict(args), "ok": response.get("ok") is True})
        return response if clock() < deadline else None

    first = invoke("get_festival", {"festival_id": request.festival_id})
    if first is None:
        return unavailable("budget_exhausted")
    first_data = first.get("data") if first.get("ok") is True else None
    issue = _detail_issue(first_data, request, as_of)
    record["first_issue"] = issue
    record["first_evidence"] = _summary(first_data)
    if issue is None:
        result = FestivalAgent(call_tool).validate(request, first, ["START", "validate_first"], calls)
        record["final_reason"] = "first_evidence_valid"
        return result, record

    if len(calls) >= max_calls or clock() >= deadline:
        return unavailable("budget_exhausted")
    decision = judge({"festival_id": request.festival_id, "q": request.q,
                      "region": request.region, "as_of": as_of.isoformat(),
                      "first_issue": issue, "first_evidence": record["first_evidence"],
                      "remaining_calls": max_calls - len(calls)})
    record["judge_used"] = True
    record["judge_decision"] = dict(decision)
    if clock() >= deadline:
        return unavailable("budget_exhausted")
    if decision.get("decision") != "recheck" or decision.get("reason") != issue:
        return unavailable("judge_abstained")

    search_args = {"q": request.q, "region": request.region,
                   "date_from": as_of.isoformat(), "date_to": as_of.isoformat(),
                   "status": "ongoing"}
    search = invoke("search_festivals", search_args)
    if search is None:
        return unavailable("budget_exhausted")
    items = search.get("data", {}).get("items") if search.get("ok") is True else None
    if not isinstance(items, list):
        return unavailable("search_unavailable")
    candidates = [item for item in items if _detail_issue(item, request, as_of) is None]
    if len(candidates) != 1:
        return unavailable("candidate_unverified")
    revised = invoke("get_festival", {"festival_id": request.festival_id})
    if revised is None:
        return unavailable("budget_exhausted")
    revised_data = revised.get("data") if revised.get("ok") is True else None
    if _detail_issue(revised_data, request, as_of) is not None:
        return unavailable("revised_evidence_invalid")
    result = FestivalAgent(call_tool).validate(request, revised,
        ["START", "reflect", "recheck", "validate_revised"], calls)
    record["final_reason"] = "revised_evidence_valid" if result.outcome == "answered" else "revised_evidence_invalid"
    return result, record


def _detail_issue(data: Any, request: FestivalRequest, as_of: date) -> str | None:
    if not isinstance(data, Mapping):
        return "source_missing"
    if data.get("festival_id") != request.festival_id:
        return "id_mismatch"
    if data.get("name") != request.q or data.get("region_code") != request.region:
        return "condition_mismatch"
    if not data.get("source") or not data.get("last_synced_at"):
        return "source_missing"
    try:
        observed = datetime.fromisoformat(data["last_synced_at"])
        start = date.fromisoformat(data["start_date"])
        end = date.fromisoformat(data["end_date"])
    except (KeyError, TypeError, ValueError):
        return "time_missing"
    if observed.tzinfo is None or start > as_of or end < as_of or data.get("event_status") != "ongoing":
        return "condition_mismatch"
    return None


def _summary(data: Any) -> dict[str, Any]:
    if not isinstance(data, Mapping):
        return {}
    return {key: data.get(key) for key in ("festival_id", "name", "region_code", "source",
        "last_synced_at", "start_date", "end_date", "event_status")}
