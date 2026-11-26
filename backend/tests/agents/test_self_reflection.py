"""W28 fixed-response checks; the judge here is not a live model."""

import unittest
from datetime import date

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


if __name__ == "__main__":
    unittest.main()
