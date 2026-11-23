"""통합 시험 — 귀갓길 흐름.

사용자가 축제를 찾고, 주변 정보를 보고, 귀갓길을 요청해 결과를 받기까지를 이어서 확인한다.
실패 흐름은 `X-Mock-Scenario` 헤더로 재현한다.
"""

import pytest
from conftest import RETURN, ROUTE_TOKEN, VISIT, Flow, assert_route_matches_festival


def test_I01_search_festival_then_return_route_ready(flow: Flow) -> None:
    """축제 검색 → 상세 → 주변 정보 → 귀갓길 접수 → 조회 → 결과가 고른 축제와 맞음."""
    found = flow.festivals(region="SEOUL", status="ongoing")
    assert [item["festival_id"] for item in found["items"]] == ["fst_000001"]
    festival_id = found["items"][0]["festival_id"]

    festival = flow.festival(festival_id)
    assert festival["name"] == found["items"][0]["name"]

    # 귀가 전에 보는 주변 정보: 셋 다 같은 축제·같은 지역으로 답해야 한다
    notices = flow.info(festival_id, "notices")
    weather = flow.info(festival_id, "weather")
    crowd = flow.info(festival_id, "crowd")
    for info in (notices, weather, crowd):
        assert info["festival_id"] == festival_id
        assert info["status"] == "ok"
        assert info["coverage"]["region_code"] == festival["region_code"]
    assert any(item["type"] == "traffic_control" for item in notices["items"])
    assert crowd["areas"][0]["congest_color"] == "yellow"

    accepted = flow.ok(
        flow.submit_route(RETURN, {"request_id": "i01-return-0001", "festival_id": festival_id,
                                   "destination": {"query": "서울역"}}),
        202,
    )
    route = flow.poll_route(accepted)

    assert flow.polls == ["processing", "ready"]
    assert route["route_request_id"] == accepted["route_request_id"]
    assert route["direction"] == "return"
    assert route["destination"] == {"type": "place", "label": "서울역"}
    assert_route_matches_festival(route, festival)
    # 교통통제는 아직 확인하지 못했다는 사실을 사용자에게 알려야 한다
    assert route["verification_status"] == "control_unverified"
    assert route["notices"]


def test_I02_request_id_follows_every_step(flow: Flow) -> None:
    """화면이 보낸 X-Request-ID가 접수·조회 응답에 그대로 돌아와 장애 추적에 쓸 수 있음."""
    trace = "trace-i02-0001"
    response = flow.submit_route(
        RETURN, {"request_id": "i02-return-0001", "festival_id": "fst_000003",
                 "destination": {"lat": 35.1151, "lng": 129.0415}},
        request_id=trace,
    )
    accepted = flow.ok(response, 202)
    assert response.headers["X-Request-ID"] == trace

    poll = flow.client.get(
        accepted["status_url"],
        headers={ROUTE_TOKEN: accepted["route_access_token"], "X-Request-ID": trace},
    )
    assert poll.headers["X-Request-ID"] == trace
    route = flow.poll_route(accepted)
    assert_route_matches_festival(route, flow.festival("fst_000003"))
    assert route["destination"]["label"] == "35.1151,129.0415"


@pytest.mark.parametrize(
    ("scenario", "final_status", "error_code"),
    [
        ("async_unavailable", "unavailable", "ROUTE_UPSTREAM_ERROR"),
        ("async_timeout", "timed_out", "ROUTE_TIMEOUT"),
    ],
)
def test_I03_route_fails_then_retry_succeeds(
    flow: Flow, scenario: str, final_status: str, error_code: str
) -> None:
    """경로 공급원 장애·시간 초과 → 다시 시도 가능하다는 안내 → 새 요청 번호로 재시도 → 성공."""
    body = {"request_id": "i03-return-0001", "festival_id": "fst_000001", "destination": {"query": "서울역"}}
    failed = flow.poll_route(flow.ok(flow.submit_route(RETURN, body, scenario=scenario), 202))

    assert failed["route_status"] == final_status
    assert failed["completed_valid_route"] is False
    assert failed["error"]["code"] == error_code
    assert failed["error"]["retryable"] is True
    assert "route_candidates" not in failed or not failed["route_candidates"]

    # 재시도는 새 request_id로 보낸다(같은 번호면 실패한 요청을 그대로 돌려받는다)
    same_again = flow.ok(flow.submit_route(RETURN, body, scenario=scenario), 202)
    assert same_again["route_request_id"] == failed["route_request_id"]

    retried = flow.poll_route(
        flow.ok(flow.submit_route(RETURN, {**body, "request_id": "i03-return-0002"}), 202)
    )
    assert retried["route_status"] == "ready"
    assert retried["route_request_id"] != failed["route_request_id"]


def test_I04_overloaded_then_retry_is_accepted(flow: Flow) -> None:
    """서버 과부하 503(재시도 가능) → 잠시 뒤 새 요청 → 접수되어 결과까지 받음."""
    body = {"request_id": "i04-return-0001", "festival_id": "fst_000001", "destination": {"query": "서울역"}}
    flow.error(flow.submit_route(RETURN, body, scenario="overloaded"), 503, "ROUTE_OVERLOADED", retryable=True)

    accepted = flow.ok(flow.submit_route(RETURN, {**body, "request_id": "i04-return-0002"}), 202)
    assert flow.poll_route(accepted)["route_status"] == "ready"


def test_I05_double_tap_submit_makes_one_request(flow: Flow) -> None:
    """버튼을 두 번 눌러 같은 요청이 두 번 와도 요청은 하나, 조회 진행도 이어짐."""
    body = {"request_id": "i05-return-0001", "festival_id": "fst_000001", "destination": {"query": "서울역"}}
    first = flow.ok(flow.submit_route(RETURN, body), 202)
    second = flow.ok(flow.submit_route(RETURN, body), 202)
    assert second["route_request_id"] == first["route_request_id"]

    # 첫 번째 응답 토큰으로 한 번, 두 번째 응답 토큰으로 한 번 조회해도 같은 요청이 진행된다
    first_poll = flow.ok(flow.client.get(first["status_url"], headers={ROUTE_TOKEN: first["route_access_token"]}))
    assert first_poll["route_status"] == "processing"
    second_poll = flow.ok(
        flow.client.get(second["status_url"], headers={ROUTE_TOKEN: second["route_access_token"]})
    )
    assert second_poll["route_status"] == "ready"

    # 같은 번호로 내용만 바꿔 보내면 충돌로 막는다
    flow.error(
        flow.submit_route(RETURN, {**body, "destination": {"query": "용산역"}}), 409, "IDEMPOTENCY_CONFLICT"
    )


def test_I06_festival_without_location(flow: Flow) -> None:
    """좌표 없는 축제: 목록·상세는 보이고, 축제 기준 경로·날씨·혼잡은 '모름'으로, 장소끼리 경로는 가능."""
    festival = flow.festival("fst_000006")
    assert festival["lat"] is None and festival["lng"] is None

    flow.error(
        flow.submit_route(RETURN, {"request_id": "i06-return-0001", "festival_id": "fst_000006",
                                   "destination": {"query": "수원역"}}),
        400, "FESTIVAL_LOCATION_UNKNOWN",
    )
    for kind in ("weather", "crowd"):
        info = flow.info("fst_000006", kind)
        assert info["status"] == "unavailable"
        assert info["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    assert flow.info("fst_000006", "notices")["status"] == "ok"  # 공지는 좌표가 없어도 된다

    accepted = flow.ok(
        flow.submit_route(RETURN, {"request_id": "i06-return-0002", "festival_id": "fst_000006",
                                   "origin": {"query": "수원역"}, "destination": {"query": "서울역"}}),
        202,
    )
    route = flow.poll_route(accepted)
    assert route["route_status"] == "ready"
    assert route["origin"]["type"] == "place"


def test_I07_visit_then_return_are_separate(flow: Flow) -> None:
    """가는 길 → 귀갓길을 이어서 요청: 방향이 섞이지 않고, 서로의 주소·토큰으로는 볼 수 없음."""
    festival = flow.festival("fst_000001")
    visit = flow.ok(
        flow.submit_route(VISIT, {"request_id": "i07-visit-0001", "festival_id": "fst_000001",
                                  "origin": {"query": "서울역"}}),
        202,
    )
    back = flow.ok(
        flow.submit_route(RETURN, {"request_id": "i07-return-0001", "festival_id": "fst_000001",
                                   "destination": {"query": "서울역"}}),
        202,
    )
    visit_route = flow.poll_route(visit)
    return_route = flow.poll_route(back)

    assert visit_route["direction"] == "visit"
    assert visit_route["destination"]["type"] == "festival"
    assert return_route["direction"] == "return"
    assert return_route["origin"]["type"] == "festival"
    assert_route_matches_festival(visit_route, festival)
    assert_route_matches_festival(return_route, festival)

    # 귀가 번호를 가는 길 주소로 → 없음, 가는 길 토큰으로 귀가 조회 → 남의 것
    flow.error(
        flow.client.get(f"{VISIT}/{back['route_request_id']}", headers={ROUTE_TOKEN: back["route_access_token"]}),
        404, "ROUTE_REQUEST_NOT_FOUND",
    )
    flow.error(
        flow.client.get(back["status_url"], headers={ROUTE_TOKEN: visit["route_access_token"]}),
        403, "FORBIDDEN",
    )
