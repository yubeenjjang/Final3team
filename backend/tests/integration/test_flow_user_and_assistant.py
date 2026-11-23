"""통합 시험 — 로그인·관심 축제·챗봇 흐름.

챗봇이 실패해도 축제 검색과 귀가 조회는 계속 쓸 수 있는지(기능 저하 시 동작)를 함께 확인한다.
"""

from conftest import AUTH, FAVORITES, RETURN, Flow, assert_route_matches_festival


def _bearer(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access']}"}


def test_I08_login_save_favorite_then_return_route_then_logout(flow: Flow) -> None:
    """가입·로그인 → 축제 검색 → 관심 저장 → 관심 목록에서 골라 귀갓길 → 로그아웃 → 관심 목록 막힘."""
    tokens = flow.sign_up_and_login("Taek")
    auth = _bearer(tokens)

    festival_id = flow.festivals(q="야시장")["items"][0]["festival_id"]
    saved = flow.ok(flow.client.put(f"{FAVORITES}/{festival_id}", headers=auth), 201)
    assert saved["festival_id"] == festival_id

    favorites = flow.ok(flow.client.get(FAVORITES, headers=auth))
    assert favorites["total"] == 1
    picked = favorites["items"][0]
    assert picked["festival_id"] == festival_id

    route = flow.poll_route(
        flow.ok(
            flow.submit_route(RETURN, {"request_id": "i08-return-0001", "festival_id": picked["festival_id"],
                                       "destination": {"query": "신길역"}}),
            202,
        )
    )
    assert_route_matches_festival(route, flow.festival(festival_id))

    logout = flow.client.post(f"{AUTH}/logout", json={"refresh_token": tokens["refresh"]}, headers=auth)
    assert logout.status_code == 204
    flow.error(flow.client.get(FAVORITES, headers=auth), 401, "UNAUTHORIZED")


def test_I09_favorites_are_private_per_user(flow: Flow) -> None:
    """두 사람이 각자 저장: 서로의 관심 목록이 섞이지 않고, 한 사람이 지워도 다른 사람 것은 남음."""
    a = _bearer(flow.sign_up_and_login("UserA"))
    b = _bearer(flow.sign_up_and_login("UserB"))

    flow.ok(flow.client.put(f"{FAVORITES}/fst_000001", headers=a), 201)
    flow.ok(flow.client.put(f"{FAVORITES}/fst_000003", headers=b), 201)
    flow.ok(flow.client.put(f"{FAVORITES}/fst_000001", headers=b), 201)

    assert [i["festival_id"] for i in flow.ok(flow.client.get(FAVORITES, headers=a))["items"]] == ["fst_000001"]
    assert flow.ok(flow.client.get(FAVORITES, headers=b))["total"] == 2

    assert flow.client.delete(f"{FAVORITES}/fst_000001", headers=a).status_code == 204
    assert flow.ok(flow.client.get(FAVORITES, headers=a))["total"] == 0
    assert flow.ok(flow.client.get(FAVORITES, headers=b))["total"] == 2


def test_I10_refresh_keeps_session_until_token_reuse(flow: Flow) -> None:
    """화면이 토큰을 새로 받아 계속 쓰다가, 옛 토큰이 다시 쓰이면(탈취 의심) 세션 전체가 끊김."""
    tokens = flow.sign_up_and_login("Refresh")
    renewed = flow.ok(flow.client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh"]}))
    new_auth = {"Authorization": f"Bearer {renewed['access_token']}"}
    flow.ok(flow.client.put(f"{FAVORITES}/fst_000001", headers=new_auth), 201)

    flow.error(flow.client.post(f"{AUTH}/refresh", json={"refresh_token": tokens["refresh"]}), 401, "REFRESH_REUSED")
    # 옛 토큰 재사용이 감지되면 새로 받은 토큰도 함께 폐기된다
    again = flow.client.post(f"{AUTH}/refresh", json={"refresh_token": renewed["refresh_token"]})
    assert again.status_code == 401


def test_I11_assistant_return_question_gives_usable_route(flow: Flow) -> None:
    """챗봇에 귀가 질문 → 작업 완료 → 챗봇이 준 경로 번호·토큰으로 귀가 화면에서 바로 조회."""
    festival = flow.festival("fst_000003")
    accepted = flow.ask("i11-ask-0001", "부산 빛 축제 끝나고 숙소로 돌아가는 길 알려줘",
                        context={"festival_id": festival["festival_id"]})
    run = flow.poll_run(accepted)

    assert flow.polls == ["running", "succeeded"]
    assert run["error"] is None
    assert [tool["tool"] for tool in run["used_tools"]] == ["get_festival", "request_return_route"]
    assert all(tool["ok"] for tool in run["used_tools"])
    assert run["evidence"][0] == {**run["evidence"][0], "type": "route", "ref": run["route_request_id"]}

    # 챗봇 답변에는 경로 내용을 넣지 않고, 경로는 귀가 API에서 받는다
    route = flow.poll_route({
        "status_url": f"{RETURN}/{run['route_request_id']}",
        "route_access_token": run["route_access_token"],
    })
    assert route["route_status"] == "ready"
    assert_route_matches_festival(route, festival)

    # 같은 대화로 이어서 질문하면 같은 대화 번호를 쓴다
    follow_up = flow.ask("i11-ask-0002", "이번 주 축제 알려줘", conversation_id=accepted["conversation_id"])
    assert follow_up["conversation_id"] == accepted["conversation_id"]


def test_I12_assistant_fails_but_core_features_still_work(flow: Flow) -> None:
    """챗봇 작업이 실패해도 안내 문구가 나오고, 축제 검색·귀갓길은 그대로 동작."""
    run = flow.poll_run(flow.ask("i12-ask-0001", "실패하는 질문"))
    assert run["run_status"] == "failed"
    assert run["error"]["code"] == "AI_AGENT_FAILED"
    assert run["error"]["retryable"] is True
    assert "귀가 조회" in run["error"]["message"]
    assert run["used_tools"][0]["ok"] is False

    assert flow.festivals()["total"] == 6
    route = flow.poll_route(
        flow.ok(
            flow.submit_route(RETURN, {"request_id": "i12-return-0001", "festival_id": "fst_000001",
                                       "destination": {"query": "서울역"}}),
            202,
        )
    )
    assert route["route_status"] == "ready"
