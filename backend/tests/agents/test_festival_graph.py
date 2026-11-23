"""Exercise real LangGraph branches, not only the direct Festival flow."""

import unittest

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest


class FestivalGraphTests(unittest.TestCase):
    def test_search_empty(self):
        result = run_festival_graph(lambda *_: {"ok": True, "data": {"items": []}}, FestivalRequest("search"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(result.transitions, ["START", "interpret", "check_slots", "select_tool", "call_tool", "validate_result", "empty_result", "END"])

    def test_missing_id_skips_tool(self):
        result = run_festival_graph(lambda *_: self.fail("must not call"), FestivalRequest("crowd"))
        self.assertEqual(result.outcome, "clarification_needed")
        self.assertEqual(result.used_tools, [])

    def test_notices_empty_result_is_answered_without_fabrication(self):
        calls = []
        def tool(name, args):
            calls.append((name, dict(args)))
            return {"ok": True, "data": {"festival_id": "fst_000001", "status": "ok", "coverage": {"scope": "national", "region_code": "SEOUL", "supported": True}, "items": []}, "is_mock": True}
        result = run_festival_graph(tool, FestivalRequest("notices", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(calls, [("get_official_notices", {"festival_id": "fst_000001"})])
        self.assertIn("공지가 없습니다", result.answer)

    def test_real_crowd_response_keeps_replacement_label(self):
        area = {"area_code": "POI009", "area_name": "광화문·덕수궁", "relation_type": "contains", "congest_level": "붐빔", "observed_at": "2026-11-23T15:25:00+09:00", "forecast": []}
        data = {"festival_id": "fst_000001", "status": "ok", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "source": "seoul_citydata", "is_mock": False, "areas": [area], "nearby_areas": [{"area_code": "POI009", "area_name": area["area_name"], "distance_m": 0, "status": "ok", "data": area, "is_estimate": True}], "is_estimate": True}
        result = run_festival_graph(lambda *_: {"ok": True, "data": data, "is_mock": False}, FestivalRequest("crowd", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual([call["tool"] for call in result.used_tools], ["get_crowd"])
        self.assertIn("최근 4주 같은 요일·시간대 평균", result.answer)
        self.assertTrue(result.evidence[0]["is_estimate"])

    def test_unsupported_crowd(self):
        data = {"festival_id": "fst_000003", "status": "unsupported", "areas": []}
        result = run_festival_graph(lambda *_: {"ok": True, "data": data}, FestivalRequest("crowd", festival_id="fst_000003"))
        self.assertEqual(result.outcome, "unsupported")
        self.assertIn("unsupported", result.transitions)

    def test_stale_crowd_is_labeled(self):
        data = {"festival_id": "fst_000001", "status": "stale", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "areas": [{"area_name": "광화문", "congest_level": "보통", "observed_at": "2026-11-22T11:55:00+09:00"}]}
        result = run_festival_graph(lambda *_: {"ok": True, "data": data}, FestivalRequest("crowd", festival_id="fst_000001"))
        self.assertEqual(result.outcome, "answered")
        self.assertIn("오래된 자료", result.answer)

    def test_retry_once_then_finish(self):
        calls = []
        def tool(*_):
            calls.append(1)
            if len(calls) == 1:
                return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
            return {"ok": True, "data": {"items": []}}
        result = run_festival_graph(tool, FestivalRequest("search"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.transitions.count("retry_once"), 1)

    def test_non_retryable_error_stops(self):
        calls = []
        def tool(*_):
            calls.append(1)
            return {"ok": False, "error": {"code": "FESTIVAL_NOT_FOUND", "retryable": False}}
        result = run_festival_graph(tool, FestivalRequest("detail", festival_id="fst_999999"))
        self.assertEqual(result.outcome, "clarification_needed")
        self.assertEqual(len(calls), 1)

    def test_route_handoff(self):
        result = run_festival_graph(lambda *_: self.fail("must not call"), FestivalRequest("route"))
        self.assertEqual(result.outcome, "handoff_required")
        self.assertEqual(result.handoff_target, "Route")

    def test_composite_search_detail_crowd_uses_first_result_id(self):
        calls = []
        def tool(name, args):
            calls.append((name, dict(args)))
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [
                    {"festival_id": "fst_000001", "name": "첫 축제", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"},
                    {"festival_id": "fst_000002", "name": "둘째 축제", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"},
                ]}}
            if name == "get_festival":
                return {"ok": True, "data": {"festival_id": args["festival_id"], "name": "첫 축제", "venue_name": "광화문광장", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"}}
            return {"ok": True, "data": {"festival_id": args["festival_id"], "status": "ok", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "areas": [{"area_name": "광화문", "congest_level": "보통", "observed_at": "2026-11-22T12:00:00+09:00"}]}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True, region="SEOUL"))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual([name for name, _ in calls], ["search_festivals", "get_festival", "get_crowd"])
        self.assertEqual(calls[1][1], {"festival_id": "fst_000001"})
        self.assertEqual(calls[2][1], {"festival_id": "fst_000001"})
        self.assertIn("광화문", result.answer)
        self.assertEqual(len(result.used_tools), 3)

    def test_composite_requires_explicit_first_choice(self):
        result = run_festival_graph(lambda *_: self.fail("must not call"), FestivalRequest("search_detail_crowd"))
        self.assertEqual(result.outcome, "clarification_needed")

    def test_composite_empty_search_stops_before_detail(self):
        calls = []
        def tool(name, args):
            calls.append(name)
            return {"ok": True, "data": {"items": []}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(calls, ["search_festivals"])

    def test_composite_unsupported_crowd_keeps_partial_answer(self):
        def tool(name, args):
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [{"festival_id": "fst_000003", "name": "부산 축제", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"}]}}
            if name == "get_festival":
                return {"ok": True, "data": {"festival_id": "fst_000003", "name": "부산 축제", "venue_name": "광복로", "source": "tourapi", "last_synced_at": "2026-11-22T09:00:00+09:00"}}
            return {"ok": True, "data": {"festival_id": "fst_000003", "status": "unsupported", "areas": []}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
        self.assertEqual(result.outcome, "partial")
        self.assertIn("광복로", result.answer)
        self.assertIn("지원하지 않습니다", result.answer)

    def test_long_real_festival_id_is_reused_with_mock_crowd_labeled(self):
        festival_id = "fst_01M835BPX17Y44VEDJM1VMZ3N6"
        item = {"festival_id": festival_id, "name": "축제", "source": "tourapi", "last_synced_at": "2026-11-23T11:57:22+09:00"}
        calls = []
        def tool(name, args):
            calls.append((name, dict(args)))
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [item], "is_mock": False}}
            if name == "get_festival":
                return {"ok": True, "data": {**item, "venue_name": "축제 장소", "is_mock": False}}
            return {"ok": True, "data": {"festival_id": festival_id, "status": "unsupported", "areas": [], "is_mock": True}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
        self.assertEqual(result.outcome, "partial")
        self.assertEqual([args["festival_id"] for _, args in calls[1:]], [festival_id, festival_id])
        self.assertIn("모의 데이터", result.answer)
        self.assertIn("지원하지 않습니다", result.answer)

    def test_composite_single_retry_still_reaches_crowd(self):
        festival_id = "fst_000001"
        item = {"festival_id": festival_id, "name": "축제", "source": "tourapi", "last_synced_at": "2026-11-23T11:57:22+09:00"}
        calls = []
        def tool(name, args):
            calls.append(name)
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [item]}}
            if len(calls) == 2:
                return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
            if name == "get_festival":
                return {"ok": True, "data": {**item, "venue_name": "축제 장소"}}
            return {"ok": True, "data": {"festival_id": festival_id, "status": "ok", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "areas": [{"area_name": "광화문", "congest_level": "보통", "observed_at": "2026-11-23T12:00:00+09:00"}]}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
        self.assertEqual(calls, ["search_festivals", "get_festival", "get_festival", "get_crowd"])
        self.assertEqual(result.outcome, "answered")
        self.assertIn("광화문", result.answer)
        self.assertNotIn("budget_exceeded", result.transitions)

    def test_composite_second_retry_exhausts_four_call_budget(self):
        festival_id = "fst_000001"
        item = {"festival_id": festival_id, "name": "축제", "source": "tourapi", "last_synced_at": "2026-11-23T11:57:22+09:00"}
        calls = []
        def tool(name, args):
            calls.append(name)
            if name == "search_festivals":
                return {"ok": True, "data": {"items": [item]}}
            if name == "get_festival" and calls.count("get_festival") == 1:
                return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
            if name == "get_festival":
                return {"ok": True, "data": {**item, "venue_name": "축제 장소"}}
            return {"ok": False, "error": {"code": "TOOL_TIMEOUT", "retryable": True}}
        result = run_festival_graph(tool, FestivalRequest("search_detail_crowd", select_first=True))
        self.assertEqual(calls, ["search_festivals", "get_festival", "get_festival", "get_crowd"])
        self.assertEqual(result.outcome, "partial")
        self.assertIn("조회 제한", result.answer)
        self.assertIn("budget_exceeded", result.transitions)

    def test_deadline_stops_before_call(self):
        ticks = iter([0.0, 31.0])
        result = run_festival_graph(lambda *_: self.fail("must not call"), FestivalRequest("search"), clock=lambda: next(ticks))
        self.assertEqual(result.outcome, "unavailable")
        self.assertEqual(result.used_tools, [])
        self.assertIn("budget_exceeded", result.transitions)


if __name__ == "__main__":
    unittest.main()
