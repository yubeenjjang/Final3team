"""Check the Festival graph through the shared W14 tool executor."""

import unittest

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest
from agents.tools import FESTIVAL_TOOLS, ToolExecutor


class FestivalSharedExecutorTests(unittest.TestCase):
    def test_composite_flow_passes_trace_and_validates_real_response_shape(self):
        requests = []
        festival_id = "fst_000001"
        responses = [
            {"is_mock": False, "items": [{"festival_id": festival_id, "name": "시험 축제", "region_code": "SEOUL", "source": "tourapi", "last_synced_at": "2026-11-24T09:00:00+09:00"}], "total": 1},
            {"is_mock": False, "festival_id": festival_id, "name": "시험 축제", "venue_name": "광장", "source": "tourapi", "last_synced_at": "2026-11-24T09:00:00+09:00"},
            {"is_mock": False, "festival_id": festival_id, "status": "ok", "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}, "source": "seoul_citydata", "observed_at": "2026-11-24T09:00:00+09:00", "areas": [{"area_name": "광화문", "congest_level": "보통", "observed_at": "2026-11-24T09:00:00+09:00"}]},
        ]

        def transport(request, timeout_s):
            requests.append(request)
            return 200, {"X-Request-ID": "req_ABCDEF123"}, responses[len(requests) - 1]

        executor = ToolExecutor("http://example.test/api/v1", FESTIVAL_TOOLS, transport=transport)
        result = run_festival_graph(
            lambda name, args: executor.execute(name, args, trace_id="req_ABCDEF123"),
            FestivalRequest("search_detail_crowd", select_first=True, region="SEOUL"),
        )
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(len(requests), 3)
        self.assertTrue(all(request.get_header("X-request-id") == "req_ABCDEF123" for request in requests))
        self.assertEqual([entry["tool"] for entry in result.used_tools], ["search_festivals", "get_festival", "get_crowd"])

    def test_unallowed_tool_is_blocked_before_transport(self):
        executor = ToolExecutor("http://example.test/api/v1", FESTIVAL_TOOLS,
                                transport=lambda *_: self.fail("HTTP must not be called"))
        response = executor.execute("request_return_route", {}, trace_id="req_ABCDEF123")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "TOOL_NOT_ALLOWED")


if __name__ == "__main__":
    unittest.main()
