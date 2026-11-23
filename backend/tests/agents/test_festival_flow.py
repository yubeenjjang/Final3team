"""Behavioral checks for the model-independent Festival state flow."""

import unittest

from agents.roles.festival import FestivalAgent, FestivalRequest


class FestivalFlowTests(unittest.TestCase):
    def test_search_empty_is_success_without_guessing(self):
        seen = []
        def tool(name, args):
            seen.append((name, args))
            return {"ok": True, "data": {"items": [], "total": 0}, "is_mock": True}
        result = FestivalAgent(tool).run(FestivalRequest("search", region="SEOUL"))
        self.assertEqual(result.outcome, "answered")
        self.assertIn("축제가 없습니다", result.answer)
        self.assertEqual(seen, [("search_festivals", {"region": "SEOUL"})])
        self.assertEqual(result.transitions[-1], "END")

    def test_search_requires_source_and_time(self):
        item = {"festival_id": "fst_000001", "name": "가상 축제", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"}
        good = FestivalAgent(lambda *_: {"ok": True, "data": {"items": [item]}, "is_mock": True}).run(FestivalRequest("search"))
        self.assertEqual(good.outcome, "answered")
        self.assertEqual(good.evidence[0]["festival_id"], "fst_000001")
        item["source"] = None
        bad = FestivalAgent(lambda *_: {"ok": True, "data": {"items": [item]}}).run(FestivalRequest("search"))
        self.assertEqual(bad.outcome, "unavailable")

    def test_detail_missing_id_does_not_call_tool(self):
        result = FestivalAgent(lambda *_: self.fail("tool must not run")).run(FestivalRequest("detail"))
        self.assertEqual(result.outcome, "clarification_needed")
        self.assertEqual(result.used_tools, [])

    def test_detail_rejects_wrong_festival(self):
        result = FestivalAgent(lambda *_: {"ok": True, "data": {"festival_id": "fst_000002"}}).run(FestivalRequest("detail", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "unavailable")

    def test_crowd_distinguishes_unsupported_stale_and_unavailable(self):
        def run(status):
            data = {"festival_id": "fst_000001", "status": status, "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "areas": [{"area_name": "광화문", "congest_level": "보통", "observed_at": "2026-11-22T12:00:00+09:00"}]}
            return FestivalAgent(lambda *_: {"ok": True, "data": data}).run(FestivalRequest("crowd", festival_id="fst_000001"))
        self.assertEqual(run("unsupported").outcome, "unsupported")
        stale = run("stale")
        self.assertEqual(stale.outcome, "answered")
        self.assertIn("오래된 자료", stale.answer)
        self.assertEqual(run("unavailable").outcome, "unavailable")

    def test_crowd_without_supported_coverage_is_not_reported_as_current(self):
        data = {"festival_id": "fst_000001", "status": "ok", "areas": [{"area_name": "광화문", "congest_level": "붐빔", "observed_at": "2026-11-22T12:00:00+09:00"}]}
        result = FestivalAgent(lambda *_: {"ok": True, "data": data}).run(FestivalRequest("crowd", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "unavailable")
        self.assertIn("지원 범위", result.answer)

    def test_retry_once_then_stop(self):
        attempts = []
        def tool(*_):
            attempts.append(1)
            return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
        result = FestivalAgent(tool).run(FestivalRequest("search"))
        self.assertEqual(len(attempts), 2)
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(result.transitions.count("retry_once"), 1)

    def test_handoff_does_not_call_route_or_admin_tool(self):
        result = FestivalAgent(lambda *_: self.fail("tool must not run")).run(FestivalRequest("route"))
        self.assertEqual(result.outcome, "handoff_required")
        self.assertEqual(result.handoff_target, "Route")


if __name__ == "__main__":
    unittest.main()
