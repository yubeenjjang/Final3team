import pytest
from fastapi.testclient import TestClient

_URL = "/api/v1/festivals"


@pytest.mark.parametrize("mode", [None, "mock"])
def test_I13_mock_accepts_single_and_multiple_statuses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, mode: str | None
) -> None:
    if mode is None:
        monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    else:
        monkeypatch.setenv("FESTIVAL_DATA", mode)

    for statuses, expected in (
        ("ongoing,upcoming", ["fst_000003", "fst_000001", "fst_000002", "fst_000005"]),
        (" ongoing , upcoming, ongoing ", ["fst_000003", "fst_000001", "fst_000002", "fst_000005"]),
        ("ongoing", ["fst_000003", "fst_000001"]),
    ):
        response = client.get(_URL, params={"status": statuses})
        assert response.status_code == 200
        assert response.headers["X-Mock"] == "true"
        body = response.json()
        assert body["is_mock"] is True
        assert body["total"] == len(expected)
        assert [item["festival_id"] for item in body["items"]] == expected


@pytest.mark.parametrize("statuses", ["ongoing,mars", "", "ongoing,", "ongoing,,upcoming"])
def test_I13_mock_rejects_invalid_statuses(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, statuses: str
) -> None:
    monkeypatch.setenv("FESTIVAL_DATA", "mock")
    response = client.get(_URL, params={"status": statuses})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_I12_x_mock_header_only_for_mock_data(client, monkeypatch) -> None:
    # 모의 모드: 축제 목록에도 X-Mock
    assert client.get("/api/v1/festivals").headers.get("X-Mock") == "true"
    # DB 모드: 축제 목록·상세 주소에는 X-Mock이 없고, 아직 모의인 날씨 주소에는 그대로
    from api.main import _serves_real_data
    from starlette.requests import Request

    def make(path: str) -> Request:
        return Request({"type": "http", "path": path, "headers": [], "method": "GET", "query_string": b""})

    monkeypatch.setenv("FESTIVAL_DATA", "db")
    assert _serves_real_data(make("/api/v1/festivals"))
    assert _serves_real_data(make("/api/v1/festivals/fst_01M835AGG6JY1CG8A3364VARPX"))
    assert not _serves_real_data(make("/api/v1/festivals/fst_000001/weather"))
    monkeypatch.setenv("FESTIVAL_DATA", "mock")
    assert not _serves_real_data(make("/api/v1/festivals"))
