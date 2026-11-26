"""Compare W28 fixed-response cases; --live calls a model for mismatch cases.

The fake festival tool never contacts the team API.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from getpass import getpass
from time import perf_counter
from uuid import uuid4
from typing import Callable

from agents.festival_graph import build_festival_graph, run_festival_graph
from agents.reflection_model import DEFAULT_MODEL, generate_reflection
from agents.roles.festival import FestivalRequest


FESTIVAL_ID = "F01"
GOOD = {"festival_id": FESTIVAL_ID, "name": "시험 축제", "region_code": "SEOUL",
        "source": "tourapi", "last_synced_at": "2026-11-26T09:00:00+09:00",
        "start_date": "2026-11-01", "end_date": "2026-11-30",
        "event_status": "ongoing", "venue_name": "시험 광장"}
SCENARIOS = ("mismatch_fixed", "mismatch_persistent", "valid_first")


def run_scenario(scenario: str, judge: Callable[[dict], dict], *, model: str = DEFAULT_MODEL) -> dict:
    """Return B0/A1 observations for one identical first response."""
    if scenario not in SCENARIOS:
        raise ValueError("unknown W28 scenario")
    tool_calls = []
    first_data = GOOD if scenario == "valid_first" else {**GOOD, "festival_id": "F02"}

    def tool(name, params):
        tool_calls.append({"name": name, "args": dict(params)})
        if name == "search_festivals":
            return {"ok": True, "data": {"items": [GOOD]}, "is_mock": True}
        data = first_data if len(tool_calls) == 1 or scenario == "mismatch_persistent" else GOOD
        return {"ok": True, "data": data, "is_mock": True}

    request = FestivalRequest("detail", festival_id=FESTIVAL_ID, q="시험 축제", region="SEOUL")
    baseline_started = perf_counter()
    baseline = run_festival_graph(lambda *_: {"ok": True,
        "data": first_data, "is_mock": True}, request)
    baseline_elapsed_ms = round((perf_counter() - baseline_started) * 1000, 2)
    started = perf_counter()
    graph = build_festival_graph(tool, as_of=date(2026, 11, 26), reflect_judge=judge)
    state = graph.invoke({"request": request})
    result = state["result"]
    report = {"run_id": str(uuid4()), "executed_at": datetime.now(timezone.utc).isoformat(),
              "scenario": scenario, "model": model if state["reflection_record"]["judge_used"] else None,
              "first_response_is_mock": True, "model_hinted_issue": False,
              "baseline": {"outcome": baseline.outcome, "answer": baseline.answer,
                           "evidence": baseline.evidence,
                           "tool_calls": len(baseline.used_tools), "elapsed_ms": baseline_elapsed_ms},
              "outcome": result.outcome,
              "answer": result.answer, "evidence": result.evidence,
              "tool_calls": tool_calls, "reflection": state["reflection_record"],
              "elapsed_ms": round((perf_counter() - started) * 1000, 2),
              "passed": (result.outcome == "answered" and
                         state["reflection_record"]["final_reason"] == "revised_evidence_valid")
                        if scenario == "mismatch_fixed" else
                        (result.outcome == "unavailable" and not result.evidence and
                         state["reflection_record"]["final_reason"] == "revised_evidence_invalid")
                        if scenario == "mismatch_persistent" else
                        (result.outcome == "answered" and
                         state["reflection_record"]["judge_used"] is False and
                         len(tool_calls) == 1),
              "improved_valid_answer": baseline.outcome != "answered" and
                                       result.outcome == "answered"}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call the judgment model for a mismatch case")
    parser.add_argument("--scenario", choices=SCENARIOS, default="mismatch_fixed")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", help="Optional JSON result path; never includes the API key")
    args = parser.parse_args()
    if args.scenario != "valid_first" and not args.live:
        parser.error("--live is required for a mismatch case")
    key = getpass("OpenAI API key (hidden; not saved): ") if args.scenario != "valid_first" else None
    if args.scenario != "valid_first" and not key:
        parser.error("API key is required")
    def judge(context):
        if key is None:
            raise AssertionError("valid first evidence must not call the model")
        return generate_reflection(context, api_key=key, model=args.model)

    report = run_scenario(args.scenario, judge, model=args.model)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
