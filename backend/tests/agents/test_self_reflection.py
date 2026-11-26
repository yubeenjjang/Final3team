"""W28 fixed-response checks; the judge here is not a live model."""

import unittest
from datetime import date

from agents.festival_graph import build_festival_graph, run_festival_graph
from agents.roles.festival import FestivalRequest
from agents.self_reflection import run_reflected_detail


REQUEST = FestivalRequest("detail", festival_id="F01", q="시험 축제", region="SEOUL")
GOOD = {"festival_id": "F01", "name": "시험 축제", "region_code": "SEOUL",
        "source": "tourapi", "last_synced_at": "2026-11-26T09:00:00+09:00",
        "start_date": "2026-11-01", "end_date": "2026-11-30",
        "event_status": "ongoing", "venue_name": "시험 광장"}


class SelfReflectionTests(unittest.TestCase):
    def run_case(self, *, second=GOOD, search_items=None, max_calls=4):
        calls = []
        def tool(name, args):
            calls.append((name, dict(args)))
            if name == "search_festivals":
                return {"ok": True, "data": {"items": search_items if search_items is not None else [GOOD]}}
            data = {**GOOD, "festival_id": "F02"} if len(calls) == 1 else second
            return {"ok": True, "data": data}
        judgments = []
        def judge(context):
            judgments.append(context)
            return {"decision": "recheck", "reason": "id_mismatch"}
        result, record = run_reflected_detail(tool, REQUEST, judge,
            as_of=date(2026, 11, 26), max_calls=max_calls)
        return result, record, calls, judgments

    def test_wrong_id_is_rechecked_and_corrected(self):
        result, record, calls, judgments = self.run_case()
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(record["first_issue"], "id_mismatch")
        self.assertEqual(record["final_reason"], "revised_evidence_valid")
        self.assertEqual([name for name, _ in calls],
                         ["get_festival", "search_festivals", "get_festival"])
        self.assertEqual(calls[1][1]["status"], "ongoing")
        self.assertEqual(result.evidence[0]["festival_id"], "F01")
        self.assertNotIn("F02", result.answer)
        self.assertEqual(judgments[0]["first_issue"], "id_mismatch")

    def test_second_wrong_id_abstains(self):
        bad = {**GOOD, "festival_id": "F02"}
        result, record, calls, _ = self.run_case(second=bad)
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(record["final_reason"], "revised_evidence_invalid")
        self.assertLessEqual(len(calls), 4)
        self.assertEqual(result.evidence, [])

    def test_upcoming_candidate_does_not_satisfy_ongoing_question(self):
        upcoming = {**GOOD, "event_status": "upcoming", "start_date": "2026-12-01"}
        result, record, calls, _ = self.run_case(search_items=[upcoming])
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(record["final_reason"], "candidate_unverified")
        self.assertEqual(len(calls), 2)

    def test_valid_first_result_does_not_recheck(self):
        calls = []
        def tool(name, args):
            calls.append(name)
            return {"ok": True, "data": GOOD}
        result, record = run_reflected_detail(tool, REQUEST,
            lambda *_: self.fail("valid evidence should not recheck"), as_of=date(2026, 11, 26))
        self.assertEqual(result.outcome, "answered")
        self.assertFalse(record["judge_used"])
        self.assertEqual(calls, ["get_festival"])

    def test_call_budget_prevents_recheck(self):
        result, record, calls, judgments = self.run_case(max_calls=1)
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(record["final_reason"], "budget_exhausted")
        self.assertEqual(len(calls), 1)
        self.assertEqual(judgments, [])

    def test_judge_cannot_accept_mismatched_id(self):
        calls = []
        def tool(name, args):
            calls.append(name)
            return {"ok": True, "data": {**GOOD, "festival_id": "F02"}}
        result, record = run_reflected_detail(tool, REQUEST,
            lambda *_: {"decision": "accept", "reason": "id_mismatch"},
            as_of=date(2026, 11, 26))
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(record["final_reason"], "judge_abstained")
        self.assertEqual(calls, ["get_festival"])

    def test_langgraph_routes_opted_in_detail_through_reflection(self):
        calls = []
        def tool(name, args):
            calls.append(name)
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [GOOD]}}
            return {"ok": True, "data": {**GOOD, "festival_id": "F02"} if len(calls) == 1 else GOOD}
        graph = build_festival_graph(tool, as_of=date(2026, 11, 26),
            reflect_judge=lambda context: {"decision": "recheck", "reason": context["first_issue"]})
        state = graph.invoke({"request": REQUEST})
        self.assertEqual(state["result"].outcome, "answered")
        self.assertEqual(state["reflection_record"]["final_reason"], "revised_evidence_valid")
        self.assertEqual(calls, ["get_festival", "search_festivals", "get_festival"])

    def test_default_graph_keeps_existing_detail_flow(self):
        result = run_festival_graph(lambda *_: {"ok": True, "data": GOOD}, REQUEST)
        self.assertEqual(result.outcome, "answered")
        self.assertNotIn("reflect", result.transitions)

    def test_reflection_missing_conditions_asks_before_tool_call(self):
        result = run_festival_graph(lambda *_: self.fail("must not call"),
            FestivalRequest("detail", festival_id="F01"),
            reflect_judge=lambda *_: self.fail("must not judge"), as_of=date(2026, 11, 26))
        self.assertEqual(result.outcome, "clarification_needed")

    def test_judge_failure_ends_without_using_wrong_id(self):
        def failed_judge(_):
            raise TimeoutError("model unavailable")
        result, record = run_reflected_detail(
            lambda *_: {"ok": True, "data": {**GOOD, "festival_id": "F02"}},
            REQUEST, failed_judge, as_of=date(2026, 11, 26))
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(record["final_reason"], "judge_unavailable")
        self.assertEqual(len(record["tool_calls"]), 1)


if __name__ == "__main__":
    unittest.main()
