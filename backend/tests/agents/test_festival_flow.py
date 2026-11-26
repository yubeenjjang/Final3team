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

    def test_crowd_replacement_value_is_labeled_as_average(self):
        data = {"festival_id": "fst_000001", "status": "ok", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "source": "seoul_citydata", "is_estimate": True, "areas": [{"area_name": "광화문", "congest_level": "붐빔", "observed_at": "2026-11-23T15:00:00+09:00"}]}
        result = FestivalAgent(lambda *_: {"ok": True, "data": data, "is_mock": False}).run(FestivalRequest("crowd", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "answered")
        self.assertIn("최근 4주 같은 요일·시간대 평균", result.answer)
        self.assertEqual(result.evidence[0]["source"], "seoul_citydata")
        self.assertTrue(result.evidence[0]["is_estimate"])

    def test_official_notices_include_source_and_effective_time(self):
        item = {"notice_id": "ntc_000001", "title": "세종대로 일부 차로 통제", "source": "seoul_topis", "published_at": "2026-11-20T09:00:00+09:00", "effective_from": "2026-11-20T18:00:00+09:00", "effective_to": "2026-12-31T23:00:00+09:00"}
        calls = []
        def tool(name, args):
            calls.append((name, dict(args)))
            return {"ok": True, "data": {"festival_id": "fst_000001", "status": "ok", "coverage": {"scope": "national", "region_code": "SEOUL", "supported": True}, "items": [item]}, "is_mock": True}
        result = FestivalAgent(tool).run(FestivalRequest("notices", festival_id="fst_000001", notice_type="traffic_control"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(calls, [("get_official_notices", {"festival_id": "fst_000001", "type": "traffic_control"})])
        self.assertIn("seoul_topis", result.answer)
        self.assertIn("효력", result.answer)
        self.assertIn("모의 데이터", result.answer)

    def test_official_notices_without_evidence_are_not_presented(self):
        data = {"festival_id": "fst_000001", "status": "ok", "coverage": {"scope": "national", "region_code": "SEOUL", "supported": True}, "items": [{"notice_id": "ntc_000001", "title": "통제"}]}
        result = FestivalAgent(lambda *_: {"ok": True, "data": data}).run(FestivalRequest("notices", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "unavailable")
        self.assertIn("출처", result.answer)

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
