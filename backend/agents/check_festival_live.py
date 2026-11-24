"""Read-only Festival Agent checks against a real festival API."""

from __future__ import annotations

import argparse
from uuid import uuid4

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest
from agents.tools import FESTIVAL_TOOLS, ToolExecutor


def _trace_id() -> str:
    return f"req_{uuid4().hex[:20]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Festival API root ending in /api/v1")
    parser.add_argument("--crowd-festival-id", help="Optional Seoul festival ID for real crowd check")
    parser.add_argument("--require-crowd-answered", action="store_true", help="Fail unless the selected public festival returns a real crowd answer")
    args = parser.parse_args()
    if args.require_crowd_answered and not args.crowd_festival_id:
        parser.error("--require-crowd-answered requires --crowd-festival-id")
    # Each Agent run gets its own executor; raw checks use a separate instance.
    raw_executor = ToolExecutor(args.base_url, FESTIVAL_TOOLS)

    def raw_tool(name, tool_args):
        return raw_executor.execute(name, tool_args, trace_id=_trace_id())

    def run_agent(request):
        executor = ToolExecutor(args.base_url, FESTIVAL_TOOLS)
        trace_id = _trace_id()
        return run_festival_graph(
            lambda name, tool_args: executor.execute(name, tool_args, trace_id=trace_id),
            request,
        )

    chosen_id = None
    for status in ("ongoing", "upcoming"):
        raw = raw_tool("search_festivals", {"status": status, "page_size": 10})
        if not raw.get("ok") or raw.get("is_mock") or raw.get("data", {}).get("is_mock") is not False:
            raise RuntimeError(f"{status} search did not return real DB data: {raw.get('error')}")
        result = run_agent(FestivalRequest("search", status=status))
        if result.outcome != "answered":
            raise RuntimeError(f"{status} agent search failed: {result.answer}")
        print(f"{status}: total={raw['data'].get('total')}, agent_evidence={len(result.evidence)}")
        if chosen_id is None and result.evidence:
            chosen_id = result.evidence[0]["festival_id"]

    if chosen_id is None:
        raise RuntimeError("No ongoing or upcoming festival was returned")
    raw_detail = raw_tool("get_festival", {"festival_id": chosen_id})
    if not raw_detail.get("ok") or raw_detail.get("is_mock") or raw_detail.get("data", {}).get("is_mock") is not False:
        raise RuntimeError(f"Detail did not return real DB data: {raw_detail.get('error')}")
    detail = run_agent(FestivalRequest("detail", festival_id=chosen_id))
    if detail.outcome != "answered" or detail.evidence[0]["festival_id"] != chosen_id:
        raise RuntimeError(f"Agent detail failed for {chosen_id}: {detail.answer}")
    print(f"detail: festival_id={chosen_id}, outcome={detail.outcome}, source={detail.evidence[0]['source']}")
    print("Real DB search/detail check passed.")

    if args.crowd_festival_id:
        crowd_id = args.crowd_festival_id
        raw_crowd_detail = raw_tool("get_festival", {"festival_id": crowd_id})
        if not raw_crowd_detail.get("ok") or raw_crowd_detail.get("is_mock") or raw_crowd_detail.get("data", {}).get("is_mock") is not False:
            raise RuntimeError(f"Crowd festival is not in the public real DB: {raw_crowd_detail.get('error')}")
        crowd_detail = run_agent(FestivalRequest("detail", festival_id=crowd_id))
        if crowd_detail.outcome != "answered" or crowd_detail.evidence[0]["festival_id"] != crowd_id:
            raise RuntimeError(f"Agent detail failed for crowd festival {crowd_id}: {crowd_detail.answer}")
        print(f"crowd_festival_detail: festival_id={crowd_id}, outcome={crowd_detail.outcome}")
        raw_crowd = raw_tool("get_crowd", {"festival_id": crowd_id})
        if not raw_crowd.get("ok") or raw_crowd.get("is_mock") or raw_crowd.get("data", {}).get("is_mock") is not False:
            raise RuntimeError(f"Crowd did not return real provider data: {raw_crowd.get('error')}")
        crowd = run_agent(FestivalRequest("crowd", festival_id=crowd_id))
        if crowd.outcome not in {"answered", "unsupported", "unavailable"}:
            raise RuntimeError(f"Unexpected crowd outcome: {crowd.outcome}")
        is_estimate = raw_crowd["data"].get("is_estimate") is True
        if is_estimate and crowd.outcome == "answered" and "최근 4주 같은 요일·시간대 평균" not in crowd.answer:
            raise RuntimeError("Replacement crowd value was not labeled as an average")
        print(f"crowd: festival_id={crowd_id}, provider_status={raw_crowd['data'].get('status')}, "
              f"agent_outcome={crowd.outcome}, is_estimate={is_estimate}")
        if args.require_crowd_answered and (raw_crowd["data"].get("status") not in {"ok", "stale"} or crowd.outcome != "answered"):
            raise RuntimeError(f"Real crowd answer was not provided: provider_status={raw_crowd['data'].get('status')}, agent_outcome={crowd.outcome}")
        if args.require_crowd_answered:
            festival_name = raw_crowd_detail["data"].get("name")
            if not isinstance(festival_name, str) or not festival_name:
                raise RuntimeError("Crowd festival has no searchable name for composite check")
            composite = run_agent(FestivalRequest("search_detail_crowd", select_first=True,
                                                  region="SEOUL", q=festival_name))
            expected_tools = ["search_festivals", "get_festival", "get_crowd"]
            if (composite.outcome != "answered"
                    or [item["tool"] for item in composite.used_tools] != expected_tools
                    or len(composite.evidence) != 3
                    or any(item.get("festival_id") != crowd_id for item in composite.evidence)):
                raise RuntimeError(f"Real composite search/detail/crowd check failed: {composite.outcome}, {composite.used_tools}")
            print(f"composite: festival_id={crowd_id}, outcome={composite.outcome}, "
                  f"tool_calls={len(composite.used_tools)}, evidence={len(composite.evidence)}")
    else:
        print("Crowd was not checked; pass --crowd-festival-id to verify a Seoul festival.")


if __name__ == "__main__":
    main()
