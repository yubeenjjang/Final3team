"""Replay a saved, real crowd API response through the Festival graph."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest, FestivalResult


def check_crowd_capture(body: dict[str, Any]) -> FestivalResult:
    festival_id = body.get("festival_id")
    if not isinstance(festival_id, str) or not festival_id or body.get("is_mock") is not False:
        raise ValueError("A real crowd response with festival_id and is_mock:false is required")

    calls = []

    def captured_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        calls.append((name, dict(args)))
        return {"ok": True, "data": body, "is_mock": False}

    result = run_festival_graph(captured_tool, FestivalRequest("crowd", festival_id=festival_id))
    if calls != [("get_crowd", {"festival_id": festival_id})]:
        raise RuntimeError(f"Unexpected tool calls: {calls}")
    if body.get("status") == "ok" and result.outcome != "answered":
        raise RuntimeError(f"Agent did not answer an OK response: {result.outcome}")
    if body.get("is_estimate") is True and result.outcome == "answered":
        if "최근 4주 같은 요일·시간대 평균" not in result.answer:
            raise RuntimeError("Replacement value was not labeled as an average")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("response_json", type=Path, help="Saved /festivals/{festival_id}/crowd JSON response")
    args = parser.parse_args()
    body = json.loads(args.response_json.read_text(encoding="utf-8-sig"))
    if not isinstance(body, dict):
        raise ValueError("The response JSON must be an object")
    result = check_crowd_capture(body)
    print(f"festival_id={body['festival_id']} api_status={body.get('status')} "
          f"agent_outcome={result.outcome} is_estimate={body.get('is_estimate')}")
    print(result.answer)


if __name__ == "__main__":
    main()
