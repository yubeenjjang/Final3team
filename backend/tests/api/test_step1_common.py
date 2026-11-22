import re
from pathlib import Path

from fastapi.testclient import TestClient

_HEALTH = "/api/v1/health"
_FESTIVALS = "/api/v1/festivals"
_REQUEST_ID = re.compile(r"req_[0-9A-Za-z]{26}")
_ALLOWED_URL = re.compile(
    r"https://tong\.visitkorea\.or\.kr/.*|"
    r"https?://localhost(?::[0-9]+)?(?:/.*)?"
)


def test_R1_openapi_and_health(client: TestClient) -> None:
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["info"] == {
        "title": "놀다가 API (mock)",
        "version": "0.1.0-mock",
    }
    assert {_HEALTH, _FESTIVALS, f"{_FESTIVALS}/{{festival_id}}"}.issubset(
        schema.json()["paths"]
    )
    health = client.get(_HEALTH)
    assert health.status_code == 200
    assert health.json()["is_mock"] is True


def test_R1_cors(client: TestClient) -> None:
    headers = (
        "x-request-id, x-route-access-token, x-run-access-token, "
        "x-mock-scenario, authorization"
    )
    for origin in ("http://localhost:3000", "http://localhost:5173"):
        preflight = client.options(
            _HEALTH,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": headers,
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["Access-Control-Allow-Origin"] == origin
        allowed = preflight.headers["Access-Control-Allow-Headers"].lower().split(", ")
        assert set(headers.split(", ")).issubset(allowed)

        response = client.get(_HEALTH, headers={"Origin": origin})
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["Access-Control-Allow-Origin"] == origin
        assert response.headers["Access-Control-Expose-Headers"] == "X-Request-ID"

    response = client.get(_HEALTH, headers={"Origin": "http://localhost:3001"})
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert "Access-Control-Allow-Origin" not in response.headers

    rejected = client.options(
        _HEALTH,
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert rejected.status_code == 400
    assert "Access-Control-Allow-Origin" not in rejected.headers
    assert rejected.json()["error"]["request_id"] == rejected.headers["X-Request-ID"]


def test_R1_store_starts_clean_before_mutation() -> None:
    from api.mocks.store import festivals

    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"
    festivals["fst_000001"].name = "시험에서 바꾼 이름"
    festivals.pop("fst_000006")


def test_R1_store_reset_restores_seed() -> None:
    from api.mocks.store import festivals, reset_store

    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"
    festivals["fst_000001"].name = "시험에서 바꾼 이름"
    festivals.clear()
    reset_store()
    assert len(festivals) == 6
    assert festivals["fst_000001"].name == "광화문 겨울빛 축제"


def test_R2_error_envelope(client: TestClient) -> None:
    for url, expected_status, expected_code in (
        (f"{_FESTIVALS}?region=MARS", 422, "VALIDATION_ERROR"),
        ("/api/v1/missing", 404, "NOT_FOUND"),
    ):
        response = client.get(url)
        assert response.status_code == expected_status
        body = response.json()
        assert set(body) == {"error"}
        assert "detail" not in body
        error = body["error"]
        assert set(error) == {"code", "message", "request_id", "retryable"}
        assert error["code"] == expected_code
        assert re.search("[가-힣]", error["message"])
        assert error["request_id"] == response.headers["X-Request-ID"]
        assert error["retryable"] is False
        if expected_status == 422:
            assert "region" in error["message"]


def test_R3_request_id_is_preserved(client: TestClient) -> None:
    for request_id in ("a", "web.MOCK-request/1", "a" * 64):
        response = client.get(_HEALTH, headers={"X-Request-ID": request_id})
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["X-Request-ID"] == request_id


def test_R3_request_id_is_generated_for_missing_or_invalid_header(client: TestClient) -> None:
    for headers in ({}, {"X-Request-ID": ""}, {"X-Request-ID": "a" * 65}):
        response = client.get(_HEALTH, headers=headers)
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert _REQUEST_ID.fullmatch(response.headers["X-Request-ID"])


def test_R3_request_id_matches_error_header(client: TestClient) -> None:
    response = client.get(
        f"{_FESTIVALS}/abc", headers={"X-Request-ID": "mock-error-id"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
    assert response.headers["X-Request-ID"] == "mock-error-id"


def test_R4_mock_marker(client: TestClient) -> None:
    for url in (_HEALTH, _FESTIVALS, f"{_FESTIVALS}/fst_000001"):
        response = client.get(url)
        assert response.status_code == 200
        assert response.json()["is_mock"] is True
        assert response.headers["X-Mock"] == "true"

    missing = client.get("/api/v1/missing")
    assert missing.status_code == 404
    assert missing.headers["X-Mock"] == "true"


def test_R5_no_external_calls() -> None:
    api_dir = Path(__file__).resolve().parents[2] / "api"
    for source in api_dir.rglob("*.py"):
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            for url in re.findall(r"""https?://[^\s"'`]*""", line):
                assert _ALLOWED_URL.fullmatch(url), f"{source}:{number} 허용되지 않은 주소 {url}"


def test_R9_health_payload(client: TestClient) -> None:
    response = client.get(_HEALTH)
    assert response.status_code == 200
    assert response.json()["is_mock"] is True
    assert response.json() == {
        "status": "ok",
        "db": "mock",
        "redis": "mock",
        "version": "0.1.0-mock",
        "is_mock": True,
    }


def test_R17_mock_doc() -> None:
    path = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    content = path.read_text(encoding="utf-8")
    for title in ("실행", "시험", "A01", "A02", "A03", "가상 축제 6건"):
        assert f"## {title}" in content
    assert "모든 값은 가상" in content
    assert "`is_mock: true`" in content
    assert "uvicorn api.main:app --reload --port 8000" in content
    assert "pytest tests/api -q" in content
    for sequence in range(1, 7):
        assert f"| `fst_{sequence:06d}` |" in content
