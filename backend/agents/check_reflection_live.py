"""Run the W28 fixed-response scenario with a real judgment model.

Use --live to make one API call. The fake festival tool never contacts the team API.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from getpass import getpass
from time import perf_counter
from uuid import uuid4

from agents.festival_graph import build_festival_graph
from agents.reflection_model import DEFAULT_MODEL, generate_reflection
from agents.roles.festival import FestivalRequest


FESTIVAL_ID = "F01"
GOOD = {"festival_id": FESTIVAL_ID, "name": "시험 축제", "region_code": "SEOUL",
        "source": "tourapi", "last_synced_at": "2026-11-26T09:00:00+09:00",
        "start_date": "2026-11-01", "end_date": "2026-11-30",
        "event_status": "ongoing", "venue_name": "시험 광장"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Call the judgment model once")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--output", help="Optional JSON result path; never includes the API key")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required to make the model call")
    key = getpass("OpenAI API key (hidden; not saved): ")
    if not key:
        parser.error("API key is required")
    tool_calls = []

    def tool(name, params):
        tool_calls.append({"name": name, "args": dict(params)})
        if name == "search_festivals":
            return {"ok": True, "data": {"items": [GOOD]}, "is_mock": True}
        return {"ok": True, "data": {**GOOD, "festival_id": "F02"} if len(tool_calls) == 1 else GOOD,
                "is_mock": True}

    request = FestivalRequest("detail", festival_id=FESTIVAL_ID, q="시험 축제", region="SEOUL")
    started = perf_counter()
    graph = build_festival_graph(tool, as_of=date(2026, 11, 26),
        reflect_judge=lambda context: generate_reflection(context, api_key=key, model=args.model))
    state = graph.invoke({"request": request})
    result = state["result"]
    report = {"run_id": str(uuid4()), "executed_at": datetime.now(timezone.utc).isoformat(),
              "scenario": "W28_F02_ID_mismatch_fixed_response", "model": args.model,
              "first_response_is_mock": True, "outcome": result.outcome,
              "answer": result.answer, "evidence": result.evidence,
              "tool_calls": tool_calls, "reflection": state["reflection_record"],
              "elapsed_ms": round((perf_counter() - started) * 1000, 2),
              "passed": result.outcome == "answered" and
                        state["reflection_record"]["first_issue"] == "id_mismatch" and
                        state["reflection_record"]["final_reason"] == "revised_evidence_valid"}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
