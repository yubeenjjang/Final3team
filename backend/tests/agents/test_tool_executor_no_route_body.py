"""AI 실행 기록에 경로 본문이 섞이지 않는지 (R04 한태경, 강사 11/23 피드백 4번 후속).

공통 도구 실행기(`backend/agents/tools`의 `ToolExecutor`, yubeen 05e4d47)는
귀가 도구 응답에서 경로 본문(`route_candidates`)과 조회 토큰(`route_access_token`)을 빼고
에이전트에 넘기며, 실행 로그에는 도구 이름·추적 ID·성공 여부·오류 코드만 남긴다.
에이전트 출력·대화 상태·`agent_runs.tool_calls`는 장기 보관되므로(DB 설계서 7-0, 백업 7일)
여기에 TMAP 경로 본문이 들어가면 24시간 삭제 규칙을 어기게 된다.

- 실제 서버 없이 `transport`에 가짜 응답을 넣어 확인한다. 표시 문자열은 합성 값이다.
- `ToolExecutor`가 아직 main에 없으면 건너뛴다(yubeen 병합 전).
- `agent_runs.tool_calls`·`assistant_runs`에 실제로 기록하는 코드가 생기면 그 경로도 이 파일에 추가한다.
"""

import json
import logging
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

BODY_MARK = "ROUTEBODY-7d41c2"          # 경로 본문 안에만 넣는 표시 문자열
TOKEN = "rrt_TESTTOKEN000000000000000"   # 조회 토큰(가짜)
DEST_TEXT = "목적지표시-서울역3번출구"       # 사용자가 입력한 목적지 원문(가짜)
ROUTE_ID = "rr_TESTROUTE01"
TRACE_ID = "req_TRACE0001ab"
BASE = "http://api.invalid/api/v1"


def _executor_module():
    try:
        from backend.agents import tools
    except ImportError as exc:
        pytest.skip(f"도구 실행기를 불러올 수 없음: {exc}")
    if not hasattr(tools, "ToolExecutor") or not hasattr(tools, "ROUTE_TOOLS"):
        pytest.skip("ToolExecutor가 아직 main에 없음 (yubeen 병합 전)")
    return tools


def _route_body(status: str = "ready") -> dict:
    return {
        "route_request_id": ROUTE_ID,
        "route_status": status,
        "route_access_token": TOKEN,
        "provider": "tmap",
        "provider_tier": "primary",
        "queried_at": "2026-11-24T21:00:00+09:00",
        "completed_valid_route": True,
        "is_mock": False,
        "route_candidates": [
            {"legs": [{"mode": "BUS", "route": f"{BODY_MARK}-버스", "path": [[37.57, 126.97], [37.55, 126.97]]}]}
        ],
    }


class FakeTransport:
    """경로 API를 흉내 낸다. 받은 요청을 남겨 토큰 전달 여부도 확인한다."""

    def __init__(self, fail_status: int | None = None) -> None:
        self.requests = []
        self.fail_status = fail_status

    def __call__(self, request, timeout_s):
        self.requests.append(request)
        headers = {"X-Request-ID": TRACE_ID}
        if self.fail_status:
            return self.fail_status, headers, {
                "error": {"code": "ROUTE_UPSTREAM_ERROR", "message": "경로 정보를 가져오지 못했어요",
                          "retryable": True, "request_id": TRACE_ID},
                "route_candidates": [{"route": BODY_MARK}],
            }
        url = request.full_url
        if request.get_method() == "POST" and url.endswith("/routes/return"):
            return 200, headers, _route_body()
        if f"/routes/return/{ROUTE_ID}" in url:
            return 200, headers, _route_body()
        if "/festivals/" in url:
            return 200, headers, {"festival_id": "fst_000001", "name": "가상 축제", "is_mock": True,
                                  "note": BODY_MARK}
        return 404, headers, {"error": {"code": "NOT_FOUND", "message": "없음", "retryable": False}}


def _route_executor(transport):
    tools = _executor_module()
    return tools.ToolExecutor(BASE, tools.ROUTE_TOOLS, transport=transport)


def _request_route(executor):
    return executor.execute(
        "request_return_route",
        {"festival_id": "fst_000001", "destination": {"query": DEST_TEXT}},
        trace_id=TRACE_ID, operation_id="op-1",
    )


def _text(value) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def test_fixture_really_contains_route_body() -> None:
    """가짜 서버 응답에 본문·토큰이 실제로 들어 있어야 아래 '없음' 확인이 의미가 있다."""
    raw = _text(_route_body())
    assert BODY_MARK in raw and TOKEN in raw


def test_request_return_route_result_has_no_route_body_or_token() -> None:
    result = _request_route(_route_executor(FakeTransport()))
    assert result["ok"] is True
    text = _text(result)
    assert BODY_MARK not in text, "경로 본문이 에이전트 결과에 남음"
    assert TOKEN not in text, "조회 토큰이 에이전트 결과에 남음"
    assert "route_candidates" not in result["data"]
    # 에이전트가 다음 단계에 쓸 값은 남아야 한다
    assert result["data"]["route_request_id"] == ROUTE_ID
    assert result["data"]["route_status"] == "ready"
    assert result["data"]["provider"] == "tmap"


def test_status_lookup_uses_kept_token_but_returns_no_body() -> None:
    transport = FakeTransport()
    executor = _route_executor(transport)
    _request_route(executor)
    result = executor.execute("get_route_request_status", {"route_request_id": ROUTE_ID}, trace_id=TRACE_ID)
    assert result["ok"] is True
    text = _text(result)
    assert BODY_MARK not in text and TOKEN not in text
    assert result["data"]["route_status"] == "ready"
    # 토큰은 결과로 내보내지 않지만 실행기 안에 보관해 상태 조회에는 써야 한다
    assert transport.requests[-1].get_header("X-route-access-token") == TOKEN


def test_execution_log_has_no_body_token_or_destination(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    executor = _route_executor(FakeTransport())
    _request_route(executor)
    executor.execute("get_route_request_status", {"route_request_id": ROUTE_ID}, trace_id=TRACE_ID)
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "agent_tool" in logged, "실행 기록 자체가 남지 않음"
    for secret in (BODY_MARK, TOKEN, DEST_TEXT):
        assert secret not in logged, f"실행 로그에 남으면 안 되는 값: {secret[:12]}…"


def test_error_response_does_not_carry_route_body() -> None:
    result = _request_route(_route_executor(FakeTransport(fail_status=502)))
    assert result["ok"] is False
    assert result["error"]["code"] == "ROUTE_UPSTREAM_ERROR"
    assert BODY_MARK not in _text(result)


def test_festival_tool_response_is_passed_through_unchanged() -> None:
    """본문 제거는 귀가 도구에만 적용된다(축제 정보까지 지우면 기능이 깨짐)."""
    tools = _executor_module()
    executor = tools.ToolExecutor(BASE, tools.FESTIVAL_TOOLS, transport=FakeTransport())
    result = executor.execute("get_festival", {"festival_id": "fst_000001"})
    assert result["ok"] is True
    assert result["data"]["note"] == BODY_MARK
