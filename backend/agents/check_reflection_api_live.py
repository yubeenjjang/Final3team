"""Run W28 against real festival HTTP responses with one injected ID fault.

The first detail response ID is intentionally corrupted after the API replies.
The recheck search and final detail use untouched API responses.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from getpass import getpass
from time import perf_counter
from typing import Callable
from uuid import uuid4

from agents.festival_graph import build_festival_graph, run_festival_graph
from agents.reflection_model import DEFAULT_MODEL, generate_reflection
from agents.roles.festival import FestivalRequest
from agents.tools import FESTIVAL_TOOLS, ToolExecutor


def run_api_scenario(executor: ToolExecutor, judge: Callable[[dict], dict], *,
                     as_of: date, model: str = DEFAULT_MODEL) -> dict:
    """Choose one ongoing Seoul festival and isolate the injected ID error."""
    trace_id = "req_" + uuid4().hex[:16]
    setup_args = {"region": "SEOUL", "date_from": as_of.isoformat(),
                  "date_to": as_of.isoformat(), "status": "ongoing", "page_size": 10}
    listing = executor.execute("search_festivals", setup_args, trace_id=trace_id)
    if listing.get("ok") is not True or listing.get("is_mock") is True:
        raise ValueError("real festival search is unavailable")
    items = listing.get("data", {}).get("items")
    if not isinstance(items, list):
        raise ValueError("festival list is malformed")
    chosen = next((item for item in items if isinstance(item, dict) and
        item.get("festival_id") and item.get("name") and
        item.get("region_code") == "SEOUL" and item.get("event_status") == "ongoing"), None)
    if chosen is None:
        raise ValueError("no ongoing Seoul festival with a usable ID")
    festival_id = chosen["festival_id"]
    preflight = executor.execute("get_festival", {"festival_id": festival_id}, trace_id=trace_id)
    data = preflight.get("data") if preflight.get("ok") is True else None
    if (preflight.get("is_mock") is True or not isinstance(data, dict) or
            data.get("festival_id") != festival_id or data.get("name") != chosen["name"] or
            data.get("region_code") != "SEOUL" or data.get("event_status") != "ongoing"):
        raise ValueError("selected festival detail is not a usable real response")

    request = FestivalRequest("detail", festival_id=festival_id, q=chosen["name"], region="SEOUL")
    faulty = {**preflight, "data": {**data, "festival_id": "F02_INJECTED"}}
    baseline = run_festival_graph(lambda *_: faulty, request)
    calls: list[dict] = []
    injected = False

    def tool(name, args):
        nonlocal injected
        response = executor.execute(name, args, trace_id=trace_id)
        calls.append({"tool": name, "args": dict(args), "ok": response.get("ok") is True,
                      "is_mock": response.get("is_mock")})
        if name == "get_festival" and not injected and response.get("ok") is True:
            injected = True
            return {**response, "data": {**response["data"], "festival_id": "F02_INJECTED"}}
        return response

    started = perf_counter()
    state = build_festival_graph(tool, reflect_judge=judge, as_of=as_of).invoke({"request": request})
    result = state["result"]
    record = state["reflection_record"]
    passed = (injected and result.outcome == "answered" and
              record["first_issue"] == "id_mismatch" and
              record["final_reason"] == "revised_evidence_valid" and
              len(calls) <= 4 and all(call["is_mock"] is False for call in calls) and
              len(result.evidence) == 1 and result.evidence[0]["festival_id"] == festival_id)
    return {"run_id": str(uuid4()), "executed_at": datetime.now(timezone.utc).isoformat(),
            "model": model, "as_of": as_of.isoformat(), "festival_id": festival_id,
            "festival_name": chosen["name"], "setup_real_api": True,
            "first_detail_id_fault_injected": True, "real_http_calls_after_setup": calls,
            "baseline": {"outcome": baseline.outcome, "evidence": baseline.evidence,
                         "tool_calls": len(baseline.used_tools)},
            "outcome": result.outcome, "answer": result.answer,
            "evidence": result.evidence, "reflection": record,
            "elapsed_ms": round((perf_counter() - started) * 1000, 2), "passed": passed}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Festival API base URL ending in /api/v1")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--as-of", type=date.fromisoformat,
                        default=datetime.now(timezone(timedelta(hours=9))).date())
    parser.add_argument("--output", help="Optional result JSON path; API key is never saved")
    args = parser.parse_args()
    key = getpass("OpenAI API key (hidden; not saved): ")
    if not key:
        parser.error("API key is required")
    executor = ToolExecutor(args.base_url, FESTIVAL_TOOLS)
    report = run_api_scenario(executor,
        lambda context: generate_reflection(context, api_key=key, model=args.model),
        as_of=args.as_of, model=args.model)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
