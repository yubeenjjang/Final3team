"""통합 시험 — 장애·재시도 화면 흐름 (I02~I06, I12~I14, R04 한태경).

삭제된 모의 전용 통합 시험(7c86adb)의 장애 시나리오를 `test_screen_flows`와 같은 환경으로 옮겼다.
축제·로그인·비서는 일회용 DB, 귀가 경로·날씨·혼잡은 모의 공급원(`X-Mock-Scenario`)을 쓴다.
개별 API 시험에 이미 있는 단일 동작은 반복하지 않고, 검색 → 상세 → 주변 정보 → 귀가로 이어지는
화면 흐름에서 지켜야 하는 연결 조건만 확인한다.

옛 시험과 달라진 점(11/26 팀장 요청에 따라 기록):
- I06: 공지는 DB 모드라 "승인된 공지 없음"으로 응답한다.
- I12: 비서 실패는 질문 문구가 아니라 워커 결과 주입으로 재현한다.
- I13: 공지는 DB 조회 오류를 주입한다(DB 공지에는 "오래됨" 상태가 없어 stale은 제외).
  혼잡은 모의 구역이 모의 축제 ID에만 연결돼 있어 DB 축제는 "미지원"이므로 미지원 상태로 확인한다.
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.auth.state import MemoryAuthState
from api.jobs.assistant_queue import PostgresAssistantQueue
from api.jobs.assistant_runner import AgentResult
from api.jobs.assistant_worker import work_once
from api.services import assistant, real_festival_info, route_rate_limit

from .conftest import checked

pytestmark = pytest.mark.db

API = "/api/v1"
RETURN = f"{API}/routes/return"
ROUTE_TOKEN = "X-Route-Access-Token"
SCENARIO = "X-Mock-Scenario"
STALE = "정보가 오래됐어요"


@pytest.fixture(autouse=True)
def fresh_route_limit(monkeypatch):
    """귀가 접수 제한(분당 10회)은 메모리 기록이라 시험끼리 쌓인다. 제한 값은 두고 기록만 새로 시작한다."""
    monkeypatch.setattr(route_rate_limit, "state", MemoryAuthState())


def mocked(response, status: int = 200, code: str | None = None) -> dict:
    """모의 공급원 응답(귀가·날씨·혼잡). 공통 `checked`는 X-Mock 헤더를 허용하지 않아 따로 둔다."""
    assert response.status_code == status, (response.request.url.path, response.status_code, response.text[:200])
    body = response.json()
    if code is not None:
        assert body["error"]["code"] == code
    return body


def request_id(tag: str) -> str:
    # 모의 경로 기록은 시험 사이에 남으므로 매번 새 번호를 쓴다
    return f"{tag}-{uuid4().hex}"


@pytest.fixture
def festival(browser, festivals, service_db):
    """검색으로 찾은 공개 DB 축제(좌표 포함)의 상세."""
    ids, key = festivals
    with service_db.begin() as db:
        db.execute(text("""
            UPDATE public.festivals
               SET venue_name = '광화문광장', latitude = 37.5759, longitude = 126.9768
             WHERE festival_id = :festival_id
        """), {"festival_id": ids["public"]})
    page = checked(browser.request("GET", f"{API}/festivals", params={"q": key}), 200)
    assert [item["festival_id"] for item in page["items"]] == [ids["public"]]
    detail = checked(browser.request("GET", f"{API}/festivals/{ids['public']}"), 200)
    assert detail["lat"] is not None and detail["lng"] is not None
    return detail


def submit(browser, festival_id: str, tag: str, *, scenario: str | None = None, headers=None, **body):
    sent = {"request_id": request_id(tag), "festival_id": festival_id, "destination": {"query": "서울역"}, **body}
    extra = dict(headers or {})
    if scenario:
        extra[SCENARIO] = scenario
    return browser.request("POST", RETURN, json=sent, headers=extra), sent


def poll(browser, accepted: dict, *, headers=None) -> dict:
    states = []
    for _ in range(5):
        body = mocked(browser.request("GET", accepted["status_url"], headers={
            ROUTE_TOKEN: accepted["route_access_token"], **(headers or {}),
        }))
        states.append(body["route_status"])
        if body["route_status"] not in ("queued", "processing"):
            return body
    pytest.fail(f"귀가 결과가 끝나지 않음: {states}")


def assert_return_from(route: dict, festival: dict) -> None:
    """귀가 결과가 화면에서 고른 축제에서 출발한다."""
    assert route["route_status"] == "ready"
    assert route["festival_id"] == festival["festival_id"]
    assert route["origin"]["lat"] == festival["lat"] and route["origin"]["lng"] == festival["lng"]
    assert route["route_candidates"]


def test_I02_request_id_follows_search_to_return_result(browser, festival):
    """화면이 보낸 X-Request-ID가 귀가 접수·조회 응답에 그대로 돌아와 장애를 추적할 수 있다."""
    trace = f"trace-{uuid4().hex[:12]}"
    response, _ = submit(browser, festival["festival_id"], "i02", headers={"X-Request-ID": trace},
                         destination={"lat": 37.5547, "lng": 126.9706})
    accepted = mocked(response, 202)
    assert response.headers["X-Request-ID"] == trace

    looked = browser.request("GET", accepted["status_url"], headers={
        ROUTE_TOKEN: accepted["route_access_token"], "X-Request-ID": trace,
    })
    assert looked.headers["X-Request-ID"] == trace
    route = poll(browser, accepted, headers={"X-Request-ID": trace})
    assert_return_from(route, festival)
    assert route["destination"]["label"] == "37.5547,126.9706"


@pytest.mark.parametrize(("scenario", "final_status", "error_code"), [
    ("async_unavailable", "unavailable", "ROUTE_UPSTREAM_ERROR"),
    ("async_timeout", "timed_out", "ROUTE_TIMEOUT"),
])
def test_I03_route_fails_then_new_request_succeeds(browser, festival, scenario, final_status, error_code):
    """경로 공급원 장애·시간 초과 → 재시도 가능 안내, 결과를 지어내지 않음 → 새 요청 번호로 재시도 → 성공."""
    response, sent = submit(browser, festival["festival_id"], "i03", scenario=scenario)
    failed = poll(browser, mocked(response, 202))
    assert failed["route_status"] == final_status
    assert failed["completed_valid_route"] is False
    assert failed["error"]["code"] == error_code and failed["error"]["retryable"] is True
    assert not failed.get("route_candidates")

    # 같은 번호로 다시 보내면 실패한 요청을 그대로 돌려받는다(화면은 새 번호로 재시도해야 한다)
    again = mocked(browser.request("POST", RETURN, json=sent, headers={SCENARIO: scenario}), 202)
    assert again["route_request_id"] == failed["route_request_id"]

    retried_response, _ = submit(browser, festival["festival_id"], "i03-retry")
    retried = poll(browser, mocked(retried_response, 202))
    assert retried["route_request_id"] != failed["route_request_id"]
    assert_return_from(retried, festival)


def test_I04_overloaded_then_retry_is_accepted(browser, festival):
    """서버 과부하 503(재시도 가능) 뒤 새 요청은 접수되어 고른 축제의 귀가 결과까지 받는다."""
    response, _ = submit(browser, festival["festival_id"], "i04", scenario="overloaded")
    error = mocked(response, 503, "ROUTE_OVERLOADED")
    assert error["error"]["retryable"] is True

    retried_response, _ = submit(browser, festival["festival_id"], "i04-retry")
    assert_return_from(poll(browser, mocked(retried_response, 202)), festival)


def test_I05_double_tap_submit_makes_one_request(browser, festival):
    """버튼을 두 번 눌러 같은 요청이 두 번 와도 요청은 하나이고, 어느 응답의 토큰으로든 같은 결과를 본다."""
    response, sent = submit(browser, festival["festival_id"], "i05")
    first = mocked(response, 202)
    second = mocked(browser.request("POST", RETURN, json=sent), 202)
    assert second["route_request_id"] == first["route_request_id"]

    via_first = poll(browser, first)
    via_second = poll(browser, second)
    assert via_first["route_request_id"] == via_second["route_request_id"]
    assert_return_from(via_second, festival)

    # 같은 번호에 다른 목적지를 보내면 앞 요청을 덮어쓰지 않고 막는다
    changed = {**sent, "destination": {"query": "용산역"}}
    mocked(browser.request("POST", RETURN, json=changed), 409, "IDEMPOTENCY_CONFLICT")


def test_I06_festival_without_location(browser, festivals):
    """좌표 없는 공개 축제: 검색·상세는 보이고, 축제 기준 귀가·날씨·혼잡은 '위치 모름', 장소끼리 경로는 가능."""
    ids, key = festivals  # 픽스처 축제는 좌표가 비어 있다
    page = checked(browser.request("GET", f"{API}/festivals", params={"q": key}), 200)
    assert [item["festival_id"] for item in page["items"]] == [ids["public"]]  # 목록에서 빠지지 않는다
    detail = checked(browser.request("GET", f"{API}/festivals/{ids['public']}"), 200)
    assert detail["lat"] is None and detail["lng"] is None

    response, _ = submit(browser, ids["public"], "i06")
    mocked(response, 400, "FESTIVAL_LOCATION_UNKNOWN")
    for kind in ("weather", "crowd"):
        info = mocked(browser.request("GET", f"{API}/festivals/{ids['public']}/{kind}"))
        assert info["status"] == "unavailable"
        assert info["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    # 공지는 좌표가 없어도 조회된다(DB 모드: 승인된 공지가 없으면 빈 목록)
    assert checked(browser.request("GET", f"{API}/festivals/{ids['public']}/notices"), 200)["status"] == "ok"

    place_to_place, _ = submit(browser, ids["public"], "i06-place", origin={"query": "수원역"})
    route = poll(browser, mocked(place_to_place, 202))
    assert route["route_status"] == "ready"
    assert route["origin"]["type"] == "place"


def test_I12_assistant_fails_but_search_and_return_still_work(browser, register, festival):
    """비서 작업이 실패해도 안내 문구가 나오고, 같은 사용자의 축제 검색·귀가 조회는 그대로 동작한다."""
    user = register()
    queued = checked(browser.request("POST", f"{API}/assistant/query", headers=user.headers, json={
        "request_id": request_id("i12"), "message": "오늘 축제 끝나고 집에 어떻게 가요?",
    }), 202)

    def agent_fails(claim):
        return AgentResult(error_code=assistant.FAILURE_CODE, retryable=True), False

    assert work_once(PostgresAssistantQueue(), agent_fails)
    run = checked(browser.request("GET", queued["status_url"], headers=user.headers), 200)
    assert run["run_status"] == "failed"
    assert run["error"]["code"] == "AI_AGENT_FAILED"
    assert "귀가 조회" in run["error"]["message"]
    assert not run.get("answer")

    found = checked(browser.request("GET", f"{API}/festivals", headers=user.headers,
                                    params={"q": festival["name"]}), 200)
    assert festival["festival_id"] in [item["festival_id"] for item in found["items"]]
    response, _ = submit(browser, festival["festival_id"], "i12", headers=user.headers)
    assert_return_from(poll(browser, mocked(response, 202), headers=user.headers), festival)


def test_I13_weather_error_or_stale_keeps_return_route(browser, festival):
    """날씨 공급원 오류·오래된 정보: 200과 상태로 알리고 값을 지어내지 않으며, 귀가 경로는 정상."""
    url = f"{API}/festivals/{festival['festival_id']}/weather"
    broken = mocked(browser.request("GET", url, headers={SCENARIO: "source_error"}))
    assert broken["status"] == "unavailable"
    assert broken["error"]["code"] == "SOURCE_RESULT_ERROR" and broken["error"]["retryable"] is True
    assert not broken.get("data")

    old = mocked(browser.request("GET", url, headers={SCENARIO: "stale"}))
    assert old["status"] == "stale" and STALE in old["notices"]
    assert old.get("data")  # 오래된 값도 보여 주되 표시를 붙인다

    fresh = mocked(browser.request("GET", url))
    assert fresh["status"] == "ok" and STALE not in fresh["notices"]

    response, _ = submit(browser, festival["festival_id"], "i13-weather")
    assert_return_from(poll(browser, mocked(response, 202)), festival)


def test_I13_notice_db_error_keeps_return_route(browser, festival, monkeypatch):
    """승인 공지 DB 조회가 실패해도 공지 화면은 재시도 가능 안내만 하고, 귀가 경로는 정상."""
    async def notice_db_down(*args, **kwargs):
        raise SQLAlchemyError("시험용 공지 조회 실패")

    # 공지 조회만 실패시킨다(browser 픽스처의 DB 설정은 그대로 둔다)
    with monkeypatch.context() as broken:
        broken.setattr(real_festival_info.repository, "approved_notices", notice_db_down)
        notices = checked(browser.request("GET", f"{API}/festivals/{festival['festival_id']}/notices"), 200)
    assert notices["status"] == "unavailable"
    assert notices["error"]["retryable"] is True
    assert not notices["items"]

    response, _ = submit(browser, festival["festival_id"], "i13-notice")
    assert_return_from(poll(browser, mocked(response, 202)), festival)


def test_I13_crowd_unsupported_keeps_return_route(browser, festival):
    """검증된 혼잡 구역이 없는 축제: 혼잡은 '미지원'으로 알리고 값을 지어내지 않으며, 귀가 경로는 정상."""
    crowd = mocked(browser.request("GET", f"{API}/festivals/{festival['festival_id']}/crowd"))
    assert crowd["status"] == "unsupported"
    assert not crowd.get("areas")
    assert crowd["notices"]

    response, _ = submit(browser, festival["festival_id"], "i13-crowd")
    assert_return_from(poll(browser, mocked(response, 202)), festival)


def test_I14_sync_ready_result_same_as_later_lookup(browser, festival):
    """바로 결과(200)를 받은 경우: 응답 헤더 토큰으로 다시 조회한 결과가 처음 받은 결과와 같다."""
    response, _ = submit(browser, festival["festival_id"], "i14", scenario="sync_ready")
    immediate = mocked(response, 200)
    assert_return_from(immediate, festival)
    assert "route_access_token" not in immediate  # API v0.5: 동기 200은 토큰을 헤더로 준다
    token = response.headers[ROUTE_TOKEN]

    later = mocked(browser.request("GET", f"{RETURN}/{immediate['route_request_id']}",
                                   headers={ROUTE_TOKEN: token}))
    assert later["route_status"] == "ready"
    for key in ("route_request_id", "festival_id", "origin", "destination", "route_candidates"):
        assert later[key] == immediate[key]
