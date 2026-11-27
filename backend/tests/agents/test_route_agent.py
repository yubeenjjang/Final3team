"""A04/A05 metadata interpretation; route body never enters agent evidence."""

import unittest

from agents.roles.route import RouteAgent, RouteRequest
from agents.tools import ROUTE_TOOLS, ToolExecutor


class RouteAgentTests(unittest.TestCase):
    def test_ready_exposes_provenance_without_route_body(self):
        def call(name, args):
            self.assertEqual(name, "request_return_route")
            self.assertEqual(args["festival_id"], "F01")
            return {"ok": True, "data": {
                "route_request_id": "RR01", "route_status": "ready",
                "completed_valid_route": True, "provider": "tmap",
                "queried_at": "2026-11-27T10:00:00+09:00", "is_mock": False,
                "route_candidates": [{"secret_path": [1, 2]}],
            }}

        result = RouteAgent(call).request(RouteRequest("F01", {"query": "서울역"}))
        self.assertEqual(result.outcome, "answered")
        self.assertEqual(result.route_request_id, "RR01")
        self.assertIn("tmap", result.answer)
        self.assertIn("2026-11-27", result.answer)
        self.assertNotIn("route_candidates", str(result))
        self.assertNotIn("secret_path", str(result))

    def test_queued_is_pending_and_status_can_finish(self):
        calls = []

        def call(name, args):
            calls.append(name)
            if name == "request_return_route":
                return {"ok": True, "data": {"route_request_id": "RR01", "route_status": "queued",
                                              "completed_valid_route": False, "retry_after_s": 2}}
            self.assertEqual(args, {"route_request_id": "RR01"})
            return {"ok": True, "data": {"route_request_id": "RR01", "route_status": "ready",
                                          "completed_valid_route": True, "provider": "kakao",
                                          "queried_at": "2026-11-27T10:01:00+09:00"}}

        agent = RouteAgent(call)
        pending = agent.request(RouteRequest("F01", {"query": "서울역"}))
        self.assertEqual(pending.outcome, "pending")
        self.assertEqual(pending.evidence["retry_after_s"], 2)
        self.assertEqual(agent.check_status(pending.route_request_id).outcome, "answered")
        self.assertEqual(calls, ["request_return_route", "get_route_request_status"])

    def test_failure_states_are_not_success(self):
        for status, code, phrase in (
            ("unavailable", "ROUTE_NO_RESULT", "찾지 못했습니다"),
            ("timed_out", "ROUTE_TIMEOUT", "초과"),
            ("rejected", "ROUTE_OVERLOADED", "요청이 몰려"),
        ):
            with self.subTest(status=status):
                agent = RouteAgent(lambda *_: {"ok": True, "data": {
                    "route_request_id": "RR01", "route_status": status,
                    "completed_valid_route": False, "error": {"code": code}}})
                result = agent.request(RouteRequest("F01", {"query": "서울역"}))
                self.assertEqual(result.outcome, "unavailable")
                self.assertIn(phrase, result.answer)
                self.assertEqual(result.evidence["error_code"], code)

    def test_missing_input_does_not_call_tool(self):
        agent = RouteAgent(lambda *_: self.fail("tool must not run"))
        self.assertEqual(agent.request(RouteRequest("", {"query": "서울역"})).outcome, "clarification_needed")
        self.assertEqual(agent.request(RouteRequest("F01", {})).outcome, "clarification_needed")

    def test_ready_without_valid_route_is_not_answered(self):
        agent = RouteAgent(lambda *_: {"ok": True, "data": {
            "route_request_id": "RR01", "route_status": "ready", "completed_valid_route": False}})
        self.assertEqual(agent.request(RouteRequest("F01", {"query": "서울역"})).outcome, "unavailable")

    def test_shared_executor_keeps_poll_token_private(self):
        requests = []

        def transport(request, _timeout):
            requests.append(request)
            if request.get_method() == "POST":
                return 202, {}, {"route_request_id": "RR01", "route_status": "queued",
                                 "route_access_token": "private-token", "retry_after_s": 2,
                                 "completed_valid_route": False}
            self.assertEqual(request.get_header("X-route-access-token"), "private-token")
            return 200, {}, {"route_request_id": "RR01", "route_status": "ready",
                             "completed_valid_route": True, "provider": "tmap",
                             "queried_at": "2026-11-27T10:00:00+09:00",
                             "route_candidates": [{"path": [[37.0, 127.0]]}]}

        executor = ToolExecutor("https://example.test/api/v1", ROUTE_TOOLS, transport=transport)
        agent = RouteAgent(lambda name, args: executor.execute(
            name, args, operation_id="route-operation-1" if name == "request_return_route" else None))
        pending = agent.request(RouteRequest("F01", {"query": "서울역"}))
        ready = agent.check_status(pending.route_request_id)
        self.assertEqual((pending.outcome, ready.outcome), ("pending", "answered"))
        self.assertNotIn("private-token", str(pending) + str(ready))
        self.assertNotIn("route_candidates", str(ready))
        self.assertEqual(len(requests), 2)


if __name__ == "__main__":
    unittest.main()
