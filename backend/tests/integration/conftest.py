"""통합 시험 공통 도구.

기능별 시험(`tests/api/`)과 달리, 여기서는 여러 API를 사용자 흐름 순서대로 이어 부른다.
모의 서버(`api.main:app`)만 쓰고 외부 API는 부르지 않는다.
"""

import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

RETURN = "/api/v1/routes/return"
VISIT = "/api/v1/routes/visit"
ASSISTANT = "/api/v1/assistant/query"
AUTH = "/api/v1/auth"
FAVORITES = "/api/v1/me/favorites"

ROUTE_TOKEN = "X-Route-Access-Token"
RUN_TOKEN = "X-Run-Access-Token"
SCENARIO = "X-Mock-Scenario"

# 조회를 몇 번까지 반복할지. 모의 서버는 2회차에 최종 상태가 되므로 넉넉하게 둔다.
MAX_POLLS = 5
ROUTE_FINAL = {"ready", "unavailable", "timed_out", "rejected"}
RUN_FINAL = {"succeeded", "failed"}


def pytest_configure() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(autouse=True)
def reset_mock_state() -> Iterator[None]:
    from api.mocks.store import reset_store

    reset_store()
    yield
    reset_store()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from api.main import app

    with TestClient(app) as test_client:
        yield test_client


class Flow:
    """사용자 흐름 한 번을 따라가는 도우미. 단계마다 공통 약속(is_mock, 오류 형식)을 같이 확인한다."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.polls: list[str] = []  # 조회할 때마다 받은 상태를 순서대로 남긴다

    # ---- 공통 확인 ----
    @staticmethod
    def ok(response: Any, status: int = 200) -> dict[str, Any]:
        assert response.status_code == status, response.text
        assert response.headers["X-Mock"] == "true"
        body = response.json()
        assert body["is_mock"] is True
        return body

    @staticmethod
    def error(response: Any, status: int, code: str, *, retryable: bool | None = None) -> dict[str, Any]:
        assert response.status_code == status, response.text
        error = response.json()["error"]
        assert error["code"] == code
        assert error["request_id"] == response.headers["X-Request-ID"]
        assert re.search("[가-힣]", error["message"]), "오류 안내는 한국어여야 한다"
        if retryable is not None:
            assert error["retryable"] is retryable
        return error

    # ---- 축제 ----
    def festivals(self, **params: Any) -> dict[str, Any]:
        return self.ok(self.client.get("/api/v1/festivals", params=params))

    def festival(self, festival_id: str) -> dict[str, Any]:
        return self.ok(self.client.get(f"/api/v1/festivals/{festival_id}"))

    def info(self, festival_id: str, kind: str, scenario: str | None = None) -> dict[str, Any]:
        headers = {SCENARIO: scenario} if scenario else {}
        return self.ok(self.client.get(f"/api/v1/festivals/{festival_id}/{kind}", headers=headers))

    # ---- 경로 ----
    def submit_route(
        self, url: str, body: dict[str, Any], scenario: str | None = None, request_id: str | None = None
    ) -> Any:
        headers = {}
        if scenario:
            headers[SCENARIO] = scenario
        if request_id:
            headers["X-Request-ID"] = request_id
        return self.client.post(url, json=body, headers=headers)

    def poll_route(self, accepted: dict[str, Any]) -> dict[str, Any]:
        """최종 상태가 나올 때까지 조회한다. 상태 주소와 토큰은 접수 응답에 있는 것만 쓴다."""
        headers = {ROUTE_TOKEN: accepted["route_access_token"]}
        for _ in range(MAX_POLLS):
            body = self.ok(self.client.get(accepted["status_url"], headers=headers))
            self.polls.append(body["route_status"])
            if body["route_status"] in ROUTE_FINAL:
                return body
            assert body["completed_valid_route"] is False
            assert body["retry_after_s"] > 0
        raise AssertionError(f"{MAX_POLLS}번 조회해도 끝나지 않음: {self.polls}")

    # ---- 챗봇 ----
    def ask(self, request_id: str, message: str, **extra: Any) -> dict[str, Any]:
        return self.ok(
            self.client.post(ASSISTANT, json={"request_id": request_id, "message": message, **extra}), 202
        )

    def poll_run(self, accepted: dict[str, Any]) -> dict[str, Any]:
        headers = {RUN_TOKEN: accepted["run_access_token"]}
        for _ in range(MAX_POLLS):
            body = self.ok(self.client.get(accepted["status_url"], headers=headers))
            self.polls.append(body["run_status"])
            if body["run_status"] in RUN_FINAL:
                return body
        raise AssertionError(f"{MAX_POLLS}번 조회해도 끝나지 않음: {self.polls}")

    # ---- 인증 ----
    def sign_up_and_login(self, name: str) -> dict[str, str]:
        credentials = {"email": f"{name}@example.com", "password": "example123"}
        self.ok(
            self.client.post(
                f"{AUTH}/signup",
                json={**credentials, "display_name": name, "birth_year": 2000, "gender": "female"},
            ),
            201,
        )
        tokens = self.ok(self.client.post(f"{AUTH}/login", json=credentials))
        return {"access": tokens["access_token"], "refresh": tokens["refresh_token"]}


@pytest.fixture
def flow(client: TestClient) -> Flow:
    return Flow(client)


def assert_route_matches_festival(route: dict[str, Any], festival: dict[str, Any]) -> None:
    """경로 결과가 고른 축제와 맞는지: 축제 번호, 지역, 축제 쪽 끝점 좌표, 경로 좌표 순서."""
    assert route["festival_id"] == festival["festival_id"]
    assert route["coverage"]["region_code"] == festival["region_code"]
    festival_end = route["origin"] if route["direction"] == "return" else route["destination"]
    assert festival_end["type"] == "festival"
    assert festival_end["name"] == festival["venue_name"]
    assert (festival_end["lat"], festival_end["lng"]) == (festival["lat"], festival["lng"])
    assert route["completed_valid_route"] is True
    assert len(route["route_candidates"]) >= 1
    for candidate in route["route_candidates"]:
        for leg in candidate["legs"]:
            for lat, lng in leg["path"]:
                # 지도에 그릴 때 [위도, 경도] 순서가 바뀌면 바다 한가운데 찍힌다
                assert 33.0 <= lat <= 39.0 and 124.0 <= lng <= 132.0
