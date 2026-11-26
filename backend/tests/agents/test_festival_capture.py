"""A saved real API response must be distinguished from a mock response."""

import unittest

from agents.check_festival_capture import check_crowd_capture


class FestivalCaptureTests(unittest.TestCase):
    def test_real_crowd_capture_reaches_agent(self):
        body = {"is_mock": False, "festival_id": "fst_000001", "status": "ok",
                "coverage": {"scope": "seoul_only", "region_code": "SEOUL", "supported": True},
                "source": "seoul_citydata", "is_estimate": False,
                "areas": [{"area_name": "숭례문", "congest_level": "보통",
                           "observed_at": "2026-11-23T16:40:00+09:00"}]}
        result = check_crowd_capture(body)
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(result.used_tools[0]["tool"], "get_crowd")
        self.assertIn("숭례문", result.answer)

    def test_mock_capture_is_rejected(self):
        with self.assertRaises(ValueError):
            check_crowd_capture({"is_mock": True, "festival_id": "fst_000001"})
