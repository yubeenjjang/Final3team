from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FESTIVALS = "/api/v1/festivals"


@pytest.mark.parametrize(
    ("endpoint", "data_field"), [("notices", "items"), ("weather", "data"), ("crowd", "areas")]
)
def test_R18_shared_validation_and_scenarios(
    client: TestClient, endpoint: str, data_field: str
) -> None:
    unknown_scenario = {"X-Mock-Scenario": "unknown"}
    invalid = client.get(f"{FESTIVALS}/bad/{endpoint}", headers=unknown_scenario)
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "festival_id" in invalid.json()["error"]["message"]

    missing = client.get(f"{FESTIVALS}/fst_999999/{endpoint}", headers=unknown_scenario)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"

    path = f"{FESTIVALS}/fst_000001/{endpoint}"
    success = client.get(path)
    assert success.status_code == 200
    assert success.headers["X-Mock"] == "true"
    body = success.json()
    assert {
        "festival_id", "status", "coverage", "source", "observed_at", "notices", "is_mock", data_field
    } <= body.keys()
    assert body["festival_id"] == "fst_000001"
    assert body["status"] == "ok"
    assert body["is_mock"] is True
    assert client.get(path, headers={"X-Mock-Scenario": "ok"}).json() == body

    stale = client.get(path, headers={"X-Mock-Scenario": "stale"})
    assert stale.status_code == 200
    assert stale.json()["status"] == "stale"
    assert stale.json()[data_field] == body[data_field]
    assert "정보가 오래됐어요" in stale.json()["notices"]

    unavailable = client.get(path, headers={"X-Mock-Scenario": "source_error"})
    assert unavailable.status_code == 200
    assert unavailable.json()["status"] == "unavailable"
    error = unavailable.json()["error"]
    assert error["code"] == "SOURCE_RESULT_ERROR"
    assert error["retryable"] is True
    assert error["message"]
    assert unavailable.json()[data_field] == (None if data_field == "data" else [])

    unknown = client.get(path, headers=unknown_scenario)
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("endpoint", ["weather", "crowd"])
@pytest.mark.parametrize("scenario", [None, "source_error", "unknown"])
def test_R18_R20_R21_no_coordinates_before_scenario(
    client: TestClient, endpoint: str, scenario: str | None
) -> None:
    headers = {"X-Mock-Scenario": scenario} if scenario is not None else {}
    response = client.get(f"{FESTIVALS}/fst_000006/{endpoint}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["error"]["code"] == "FESTIVAL_LOCATION_UNKNOWN"
    assert body["error"]["retryable"] is False
    assert body["error"]["message"]


def test_R19_active_notices_and_filters(client: TestClient) -> None:
    path = f"{FESTIVALS}/fst_000001/notices"
    response = client.get(path)
    assert response.status_code == 200
    body = response.json()
    assert body["coverage"] == {"scope": "national", "region_code": "SEOUL", "supported": True}
    assert body["observed_at"] == "2026-11-22T12:00:00+09:00"
    assert [item["notice_id"] for item in body["items"]] == ["ntc_000001", "ntc_000002"]
    traffic, operation = body["items"]
    assert traffic == {
        "notice_id": "ntc_000001",
        "type": "traffic_control",
        "title": "세종대로 일부 차로 통제",
        "content": traffic["content"],
        "effective_from": "2026-11-20T18:00:00+09:00",
        "effective_to": "2026-12-31T23:00:00+09:00",
        "source": "seoul_topis",
        "source_url": traffic["source_url"],
        "published_at": traffic["published_at"],
        "control_version": "ctl-0001",
    }
    assert traffic["content"]
    assert datetime.fromisoformat(traffic["published_at"]).tzinfo is not None
    assert operation["type"] == "operation"
    assert operation["title"] == "점등 시간 18:00~23:00 안내"
    assert operation["source"] == "operator"
    assert operation["control_version"] is None

    all_notices = client.get(path, params={"active_only": "false"})
    assert all_notices.status_code == 200
    assert [item["notice_id"] for item in all_notices.json()["items"]] == [
        "ntc_000001", "ntc_000002", "ntc_000003"
    ]
    ended = all_notices.json()["items"][-1]
    assert ended["type"] == "bus_detour"
    assert ended["title"] == "지난 우회 운행 안내(종료)"
    assert ended["source"] == "operator"

    filtered = client.get(path, params={"type": "traffic_control"})
    assert filtered.status_code == 200
    assert filtered.json()["items"] == [traffic]

    invalid = client.get(path, params={"type": "parade"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("festival_id", ["fst_000003", "fst_000006"])
def test_R19_empty_notices_even_without_coordinates(client: TestClient, festival_id: str) -> None:
    response = client.get(f"{FESTIVALS}/{festival_id}/notices")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["items"] == []
    assert body["notices"] == ["확인할 수 있는 공지 자료가 없어요"]


@pytest.mark.parametrize(
    ("festival_id", "region", "nx", "ny", "temperature", "precipitation", "precipitation_type"),
    [
        ("fst_000001", "SEOUL", 60, 127, 4.5, 0.0, "none"),
        ("fst_000003", "BUSAN", 97, 74, 9.0, 0.0, "none"),
        ("fst_000005", "GANGWON", 84, 123, -3.0, 0.5, "snow"),
    ],
)
def test_R20_weather_by_region(
    client: TestClient,
    festival_id: str,
    region: str,
    nx: int,
    ny: int,
    temperature: float,
    precipitation: float,
    precipitation_type: str,
) -> None:
    response = client.get(f"{FESTIVALS}/{festival_id}/weather")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["source"] == "kma"
    assert body["coverage"] == {"scope": "national", "region_code": region, "supported": True}
    assert body["observed_at"] == "2026-11-22T11:00:00+09:00"
    assert body["data"] == {
        "observed_at": body["observed_at"],
        "temperature_c": temperature,
        "precipitation_mm": precipitation,
        "precipitation_type": precipitation_type,
        "grid": {"nx": nx, "ny": ny},
        "forecast": {"status": "unverified"},
    }


def _assert_no_demographic_keys(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert "male" not in key.casefold()
            assert "rate" not in key.casefold()
            _assert_no_demographic_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_demographic_keys(child)


def test_R21_verified_crowd_area_and_forecast(client: TestClient) -> None:
    response = client.get(f"{FESTIVALS}/fst_000001/crowd")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["coverage"] == {"scope": "seoul_only", "region_code": "SEOUL", "supported": True}
    assert body["source"] == "seoul_citydata"
    assert body["observed_at"] == "2026-11-22T11:55:00+09:00"
    (area,) = body["areas"]
    assert area == {
        "area_code": "POI009",
        "area_name": "광화문·덕수궁",
        "relation_type": "contains",
        "congest_level": "보통",
        "congest_color": "yellow",
        "congest_message": "사람이 몰려 있을 수 있지만 크게 붐비지는 않아요.(모의)",
        "population_min": 48000,
        "population_max": 50000,
        "observed_at": body["observed_at"],
        "forecast": area["forecast"],
    }
    assert len(area["forecast"]) == 3
    for forecast in area["forecast"]:
        assert forecast.keys() == {"time", "congest_level", "population_min", "population_max"}
    _assert_no_demographic_keys(body)


@pytest.mark.parametrize(
    ("festival_id", "region", "supported", "notice"),
    [
        ("fst_000002", "SEOUL", True, "이 축제는 검증된 혼잡 구역 연결이 없어요"),
        ("fst_000003", "BUSAN", False, "이 지역은 아직 지원하지 않아요"),
    ],
)
@pytest.mark.parametrize("scenario", [None, "source_error", "unknown"])
def test_R21_unsupported_crowd_keeps_coverage_and_precedes_scenario(
    client: TestClient, festival_id: str, region: str, supported: bool, notice: str, scenario: str | None
) -> None:
    headers = {"X-Mock-Scenario": scenario} if scenario is not None else {}
    response = client.get(f"{FESTIVALS}/{festival_id}/crowd", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["coverage"] == {"scope": "seoul_only", "region_code": region, "supported": supported}
    assert body["areas"] == []
    assert body["notices"] == [notice]
    _assert_no_demographic_keys(body)


def test_R17_mock_doc_step5() -> None:
    doc = Path(__file__).resolve().parents[2] / "api" / "MOCK_API.md"
    content = doc.read_text(encoding="utf-8")
    assert {
        "## A07 공지·통제",
        "## A09 날씨",
        "## A10 혼잡 구역",
        "## A11 관심 축제 목록",
        "## A12 관심 축제 저장",
        "## A13 관심 축제 삭제",
    } <= set(content.splitlines())
    assert "`POST /api/v1/assistant/query`" in content
    assert "curl -sS -X POST 'http://localhost:8000/api/v1/assistant/query'" in content
    assert "`stale`" in content and "`source_error`" in content
