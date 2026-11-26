"""Reproduce a Festival partial answer when time or call budget runs out."""

from __future__ import annotations

from time import perf_counter

from agents.festival_graph import MAX_TOOL_CALLS, run_festival_graph
from agents.roles.festival import FestivalRequest


FESTIVAL_ID = "fst_budget_fixture"
ITEM = {"festival_id": FESTIVAL_ID, "name": "시험 축제", "source": "tourapi",
        "last_synced_at": "2026-11-26T09:00:00+09:00"}


def check_deadline() -> None:
    ticks = iter([0.0, 0.1, 0.2, 0.3, 0.4, 30.1])
    calls = []

    def tool(name, args):
        calls.append(name)
        if name == "search_festivals":
            return {"ok": True, "data": {"items": [ITEM]}}
        if name == "get_festival":
            return {"ok": True, "data": {**ITEM, "venue_name": "시험 광장"}}
        raise AssertionError("crowd tool must not run after the deadline")

    start = perf_counter()
    result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True),
                                clock=lambda: next(ticks))
    elapsed_ms = round((perf_counter() - start) * 1000, 3)
    assert calls == ["search_festivals", "get_festival"]
    assert result.outcome == "partial" and "시험 광장" in result.answer
    assert "혼잡 정보를 확인할 수 없습니다" in result.answer
    assert "budget_exceeded" in result.transitions
    print(f"deadline: simulated_elapsed_s=30.1, wall_elapsed_ms={elapsed_ms}, "
          f"calls={len(calls)}, outcome={result.outcome}, answer={result.answer}")


def check_call_limit() -> None:
    calls = []

    def tool(name, args):
        calls.append(name)
        if name == "search_festivals":
            return {"ok": True, "data": {"items": [ITEM]}}
        if name == "get_festival" and calls.count(name) == 1:
            return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
        if name == "get_festival":
            return {"ok": True, "data": {**ITEM, "venue_name": "시험 광장"}}
        return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}

    start = perf_counter()
    result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
    elapsed_ms = round((perf_counter() - start) * 1000, 3)
    assert calls == ["search_festivals", "get_festival", "get_festival", "get_crowd"]
    assert len(calls) == MAX_TOOL_CALLS and result.outcome == "partial"
    assert "시험 광장" in result.answer and "혼잡 정보를 확인할 수 없습니다" in result.answer
    assert "budget_exceeded" in result.transitions
    print(f"call_limit: wall_elapsed_ms={elapsed_ms}, calls={len(calls)}, "
          f"outcome={result.outcome}, answer={result.answer}")


if __name__ == "__main__":
    check_deadline()
    check_call_limit()
