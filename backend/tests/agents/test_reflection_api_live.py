"""Exercise the real-API runner contract with an in-memory HTTP transport."""

import unittest
from datetime import date

from agents.check_reflection_api_live import run_api_scenario
from agents.tools import FESTIVAL_TOOLS, ToolExecutor


DETAIL = {"is_mock": False, "festival_id": "fst_test_01", "name": "시험 축제",
          "region_code": "SEOUL", "event_status": "ongoing",
          "source": "tourapi", "last_synced_at": "2026-11-26T09:00:00+09:00",
          "start_date": "2026-11-01", "end_date": "2026-11-30",
          "venue_name": "시험 광장"}


class ReflectionApiLiveTests(unittest.TestCase):
    def test_only_first_detail_id_is_injected(self):
        requests = []
        def transport(request, _timeout):
            requests.append(request)
            if "/festivals?" in request.full_url:
                return (200, {"X-Request-ID": "req_W28API001"},
                        {"is_mock": False, "items": [DETAIL], "total": 1})
            return 200, {"X-Request-ID": "req_W28API001"}, DETAIL
        executor = ToolExecutor("http://example.test/api/v1", FESTIVAL_TOOLS, transport=transport)
        report = run_api_scenario(executor,
            lambda context: {"decision": "recheck", "reason": context["first_issue"]},
            as_of=date(2026, 11, 26), model="fixed-judge")
        self.assertTrue(report["passed"])
        self.assertEqual(report["baseline"]["outcome"], "unavailable")
        self.assertEqual(report["evidence"][0]["festival_id"], "fst_test_01")
        self.assertEqual(len(requests), 5)  # setup search/detail + three graph calls
        self.assertTrue(all("F02_INJECTED" not in request.full_url for request in requests))
        self.assertTrue(all(call["is_mock"] is False for call in report["real_http_calls_after_setup"]))

    def test_mock_catalog_is_rejected_before_judgment(self):
        executor = ToolExecutor("http://example.test/api/v1", FESTIVAL_TOOLS,
            transport=lambda *_: (200, {}, {"is_mock": True, "items": [DETAIL]}))
        with self.assertRaisesRegex(ValueError, "real festival search"):
            run_api_scenario(executor, lambda *_: self.fail("must not judge"),
                             as_of=date(2026, 11, 26))


if __name__ == "__main__":
    unittest.main()
