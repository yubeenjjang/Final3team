"""Read-only Festival Agent search/detail check against a real festival API."""

from __future__ import annotations

import argparse

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest
from agents.tools.festival_api import FestivalApiTools


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True, help="Festival API root ending in /api/v1")
    args = parser.parse_args()
    tool = FestivalApiTools(args.base_url)

    chosen_id = None
    for status in ("ongoing", "upcoming"):
        raw = tool("search_festivals", {"status": status, "page_size": 10})
        if not raw.get("ok") or raw.get("is_mock") or raw.get("data", {}).get("is_mock") is not False:
            raise RuntimeError(f"{status} search did not return real DB data: {raw.get('error')}")
        result = run_festival_graph(tool, FestivalRequest("search", status=status))
        if result.outcome != "answered":
            raise RuntimeError(f"{status} agent search failed: {result.answer}")
        print(f"{status}: total={raw['data'].get('total')}, agent_evidence={len(result.evidence)}")
        if chosen_id is None and result.evidence:
            chosen_id = result.evidence[0]["festival_id"]

    if chosen_id is None:
        raise RuntimeError("No ongoing or upcoming festival was returned")
    raw_detail = tool("get_festival", {"festival_id": chosen_id})
    if not raw_detail.get("ok") or raw_detail.get("is_mock") or raw_detail.get("data", {}).get("is_mock") is not False:
        raise RuntimeError(f"Detail did not return real DB data: {raw_detail.get('error')}")
    detail = run_festival_graph(tool, FestivalRequest("detail", festival_id=chosen_id))
    if detail.outcome != "answered" or detail.evidence[0]["festival_id"] != chosen_id:
        raise RuntimeError(f"Agent detail failed for {chosen_id}: {detail.answer}")
    print(f"detail: festival_id={chosen_id}, outcome={detail.outcome}, source={detail.evidence[0]['source']}")
    print("Real DB search/detail check passed. Crowd was not checked.")


if __name__ == "__main__":
    main()
