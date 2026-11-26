from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from api.main import app
from api.schemas.festival_info import FacilityItem
from api.services import facilities

URL = "/api/v1/festivals/fst_000001/facilities"


def test_facility_categories_distance_limit_and_unsupported(monkeypatch):
    monkeypatch.setenv("FACILITIES_PROVIDER", "real")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.setattr(facilities, "nearby_facility_items", AsyncMock(return_value=[
        FacilityItem(facility_id="far", category="parking", name="먼 주차장", lat=37.9, lng=127.0, source="test", distance_m=0),
        FacilityItem(facility_id="b", category="parking", name="두 번째", lat=37.576, lng=126.977, source="test", distance_m=0),
        FacilityItem(facility_id="a", category="parking", name="첫 번째", lat=37.5759, lng=126.9768, source="test", distance_m=0),
    ]))
    with TestClient(app) as client:
        response = client.get(URL, params={"categories": "parking,locker,parking", "limit_per_category": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["is_mock"] is False
    assert body["categories_status"] == {"parking": "ok", "locker": "unsupported"}
    assert len(body["items"]) == 1
    assert body["items"][0]["facility_id"] == "a"


def test_facility_validation_and_unverified(monkeypatch):
    monkeypatch.setenv("FACILITIES_PROVIDER", "real")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.setattr(facilities, "nearby_facility_items", AsyncMock(return_value=[]))
    monkeypatch.setattr(facilities.kakao_places, "nearby_places", AsyncMock(return_value=[]))
    with TestClient(app) as client:
        assert client.get(URL, params={"categories": "parking,bogus"}).status_code == 422
        assert client.get(URL, params={"radius_m": 99}).status_code == 422
        assert client.get(URL, params={"limit_per_category": 51}).status_code == 422
        body = client.get(URL, params={"categories": "parking,food"}).json()
    assert body["categories_status"] == {"parking": "unverified", "food": "unverified"}
    assert body["items"] == []
    assert body["status"] == "unverified"


def _kakao_item(category, facility_id):
    return FacilityItem(
        facility_id=f"kakao:{facility_id}", category=category, name=facility_id,
        lat=37.576, lng=126.977, distance_m=120.0, source="kakao_local",
    )


def test_kakao_fallback_only_for_empty_subway_parking_hospital(monkeypatch):
    """시설 DB에 없는 지역(서울 밖)은 지하철역·주차장·병원만 카카오로 보충한다."""
    monkeypatch.setenv("FACILITIES_PROVIDER", "real")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.setattr(facilities, "nearby_facility_items", AsyncMock(return_value=[
        FacilityItem(facility_id="p1", category="parking", name="공영주차장", lat=37.5759, lng=126.9768, source="test", distance_m=0),
    ]))
    calls = []

    async def fake_places(category, lat, lng, radius_m, limit):
        calls.append(category)
        return [_kakao_item(category, f"{category}_1")]

    monkeypatch.setattr(facilities.kakao_places, "nearby_places", fake_places)
    with TestClient(app) as client:
        body = client.get(URL, params={"categories": "subway_station,bus_stop,parking,hospital,toilet"}).json()
    assert sorted(calls) == ["hospital", "subway_station"]  # DB에 있는 주차장·카카오 분류 없는 버스·화장실은 안 부름
    assert body["categories_status"] == {
        "subway_station": "ok", "bus_stop": "unverified", "parking": "ok", "hospital": "ok", "toilet": "unverified",
    }
    assert {item["facility_id"] for item in body["items"]} == {"p1", "kakao:subway_station_1", "kakao:hospital_1"}
    assert body["status"] == "ok"
    assert any("카카오" in notice for notice in body["notices"])


def test_kakao_fallback_failure_keeps_unverified(monkeypatch):
    monkeypatch.setenv("FACILITIES_PROVIDER", "real")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    monkeypatch.setattr(facilities, "nearby_facility_items", AsyncMock(return_value=[]))
    monkeypatch.setattr(facilities.kakao_places, "nearby_places", AsyncMock(return_value=None))
    with TestClient(app) as client:
        response = client.get(URL, params={"categories": "subway_station,parking,hospital"})
    assert response.status_code == 200
    body = response.json()
    assert body["categories_status"] == {"subway_station": "unverified", "parking": "unverified", "hospital": "unverified"}
    assert body["status"] == "unverified"
    assert body["items"] == []


def test_kakao_fallback_not_called_in_mock_mode(monkeypatch):
    monkeypatch.setenv("FACILITIES_PROVIDER", "mock")
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    places = AsyncMock(return_value=[])
    monkeypatch.setattr(facilities.kakao_places, "nearby_places", places)
    with TestClient(app) as client:
        assert client.get(URL, params={"categories": "subway_station,parking,hospital"}).status_code == 200
    places.assert_not_called()
