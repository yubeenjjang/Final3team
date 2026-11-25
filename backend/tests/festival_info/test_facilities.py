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
