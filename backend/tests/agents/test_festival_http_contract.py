"""Exercise the shared API error and crowd-status contract through the agent."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from agents.festival_graph import run_festival_graph
from agents.roles.festival import FestivalRequest
from agents.tools.festival_api import FestivalApiTools


FESTIVAL_ID = "fst_000001"


class _Response(io.BytesIO):
    def __init__(self, body):
        super().__init__(json.dumps(body).encode("utf-8"))
        self.headers = {"X-Request-ID": "req_test"}


def _http_error(status, code, retryable):
    body = {"error": {"code": code, "message": "tool failed", "retryable": retryable}}
    return HTTPError("http://example.test", status, code, {}, _Response(body))


class FestivalHttpContractTests(unittest.TestCase):
    def setUp(self):
        self.tool = FestivalApiTools("http://example.test/api/v1")

    def test_not_found_404_asks_for_reselection_without_retry(self):
        calls = []

        def urlopen(request, timeout):
            calls.append(request.full_url)
            raise _http_error(404, "FESTIVAL_NOT_FOUND", False)

        with patch("agents.tools.festival_api.urlopen", side_effect=urlopen):
            result = run_festival_graph(self.tool, FestivalRequest("detail", festival_id=FESTIVAL_ID))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.outcome, "clarification_needed")
        self.assertIn("다시 선택", result.answer)
        self.assertNotIn("retry_once", result.transitions)
        self.assertEqual(result.used_tools[0]["error_code"], "FESTIVAL_NOT_FOUND")

    def test_transient_503_retries_once_then_answers(self):
        calls = []
        detail = {"is_mock": False, "festival_id": FESTIVAL_ID, "name": "시험 축제",
                  "venue_name": "광장", "source": "tourapi", "last_synced_at": "2026-11-24T09:00:00+09:00"}

        def urlopen(request, timeout):
            calls.append(request.full_url)
            if len(calls) == 1:
                raise _http_error(503, "TOOL_HTTP_ERROR", True)
            return _Response(detail)

        with patch("agents.tools.festival_api.urlopen", side_effect=urlopen):
            result = run_festival_graph(self.tool, FestivalRequest("detail", festival_id=FESTIVAL_ID))
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(result.transitions.count("retry_once"), 1)

    def test_unsupported_crowd_200_ends_without_retry(self):
        calls = []
        crowd = {"is_mock": False, "festival_id": FESTIVAL_ID, "status": "unsupported",
                 "coverage": {"scope": "seoul_only", "region_code": "BUSAN", "supported": False}, "areas": []}

        def urlopen(request, timeout):
            calls.append(request.full_url)
            return _Response(crowd)

        with patch("agents.tools.festival_api.urlopen", side_effect=urlopen):
            result = run_festival_graph(self.tool, FestivalRequest("crowd", festival_id=FESTIVAL_ID))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.outcome, "unsupported")
        self.assertNotIn("retry_once", result.transitions)
