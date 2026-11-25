import asyncio

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from api.mocks.store import festivals
from api.schemas.festivals import FestivalDetail, FestivalPage, FestivalQuery
from api.services import festival_store
from api.services.festival_lookup import find_festival
from tests.api.test_step5_favorites import _register_and_login

_DB_ID = "fst_01M835BPX17Y44VEDJM1VMZ3N6"
_UNKNOWN_ID = "fst_999999"
_FAVORITES = "/api/v1/me/favorites"


@pytest.fixture
def db_festival(monkeypatch: pytest.MonkeyPatch) -> FestivalDetail:
    festival = festivals["fst_000001"].model_copy(update={
        "festival_id": _DB_ID,
        "name": "시험 축제",
        "venue_name": "시험 축제 광장",
        "is_mock": False,
    })

    async def get_festival(festival_id: str) -> FestivalDetail | None:
        return festival if festival_id == _DB_ID else None

    monkeypatch.setenv("FESTIVAL_DATA", "db")
    monkeypatch.setattr(festival_store, "get_festival", get_festival)
    return festival


def _assert_mock_response(response: Response, status: int) -> None:
    assert response.status_code == status
    assert response.headers["X-Mock"] == "true"
    assert response.json()["is_mock"] is True


def test_I14_mock_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FESTIVAL_DATA", raising=False)
    festival = asyncio.run(find_festival("fst_000001"))
    assert festival == festivals["fst_000001"]
    assert asyncio.run(find_festival(_UNKNOWN_ID)) is None


def test_I14_db_lookup_and_return_route(client: TestClient, db_festival: FestivalDetail) -> None:
    assert asyncio.run(find_festival(_DB_ID)) == db_festival
    assert asyncio.run(find_festival("fst_000001")) is None

    request = {"request_id": "lookup-route-01", "destination": {"query": "서울역"}}
    response = client.post("/api/v1/routes/return", json={**request, "festival_id": _DB_ID})
    _assert_mock_response(response, 202)
    queued = response.json()
    headers = {"X-Route-Access-Token": queued["route_access_token"]}
    first = client.get(queued["status_url"], headers=headers)
    _assert_mock_response(first, 200)
    assert first.json()["route_status"] == "processing"
    second = client.get(queued["status_url"], headers=headers)
    _assert_mock_response(second, 200)
    assert second.json()["route_status"] == "ready"
    assert second.json()["origin"]["name"] == db_festival.venue_name
    assert second.json()["origin"]["lat"] == db_festival.lat
    assert second.json()["origin"]["lng"] == db_festival.lng

    missing = client.post("/api/v1/routes/return", json={**request, "festival_id": _UNKNOWN_ID})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"


@pytest.mark.parametrize("endpoint", ["weather", "notices", "crowd"])
def test_I14_db_festival_info(client: TestClient, db_festival: FestivalDetail, endpoint: str) -> None:
    response = client.get(f"/api/v1/festivals/{_DB_ID}/{endpoint}")
    _assert_mock_response(response, 200)
    assert response.json()["coverage"]["region_code"] == db_festival.region_code
    missing = client.get(f"/api/v1/festivals/{_UNKNOWN_ID}/{endpoint}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"


def test_I14_db_favorites(client: TestClient, db_festival: FestivalDetail) -> None:
    headers, _ = _register_and_login(client, "Lookup")
    path = f"{_FAVORITES}/{_DB_ID}"
    _assert_mock_response(client.put(path, headers=headers), 201)
    _assert_mock_response(client.put(path, headers=headers), 200)

    listed = client.get(_FAVORITES, headers=headers)
    _assert_mock_response(listed, 200)
    (item,) = listed.json()["items"]
    assert item["festival_id"] == _DB_ID
    assert item["name"] == db_festival.name
    missing = client.put(f"{_FAVORITES}/{_UNKNOWN_ID}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"
    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(_FAVORITES, headers=headers).json()["items"] == []


@pytest.mark.parametrize("selection", ["explicit", "ongoing", "empty"])
def test_I14_db_assistant_route(
    client: TestClient, db_festival: FestivalDetail, monkeypatch: pytest.MonkeyPatch, selection: str
) -> None:
    async def list_festivals(query: FestivalQuery) -> FestivalPage:
        assert selection != "explicit"
        assert query == FestivalQuery(status="ongoing", page_size=1)
        items = [] if selection == "empty" else [db_festival]
        return FestivalPage(items=items, total=len(items), page=1, page_size=1, is_mock=False)

    monkeypatch.setattr(festival_store, "list_festivals", list_festivals)
    context = {"festival_id": _DB_ID} if selection == "explicit" else {}
    accepted = client.post("/api/v1/assistant/query", json={
        "request_id": "lookup-assistant-01", "message": "귀가하고 싶어", "context": context,
    })
    _assert_mock_response(accepted, 202)
    run = accepted.json()
    headers = {"X-Run-Access-Token": run["run_access_token"]}
    assert client.get(run["status_url"], headers=headers).json()["run_status"] == "running"
    response = client.get(run["status_url"], headers=headers)
    _assert_mock_response(response, 200)
    outcome = response.json()
    assert outcome["run_status"] == "succeeded"
    assert outcome["answer"]
    if selection == "empty":
        assert outcome["route_request_id"] is None
        assert outcome["route_access_token"] is None
    else:
        route_id = outcome["route_request_id"]
        route = client.get(f"/api/v1/routes/return/{route_id}", headers={
            "X-Route-Access-Token": outcome["route_access_token"],
        })
        _assert_mock_response(route, 200)
        assert route.json()["festival_id"] == _DB_ID


def test_I14_db_assistant_festival_answer(client: TestClient, db_festival: FestivalDetail) -> None:
    accepted = client.post("/api/v1/assistant/query", json={
        "request_id": "lookup-assistant-02",
        "message": "이 축제 알려줘",
        "context": {"festival_id": _DB_ID},
    })
    _assert_mock_response(accepted, 202)
    run = accepted.json()
    headers = {"X-Run-Access-Token": run["run_access_token"]}
    assert client.get(run["status_url"], headers=headers).json()["run_status"] == "running"
    response = client.get(run["status_url"], headers=headers)
    _assert_mock_response(response, 200)
    outcome = response.json()
    assert outcome["run_status"] == "succeeded"
    assert db_festival.name in outcome["answer"]
    assert outcome["route_request_id"] is None
    (evidence,) = outcome["evidence"]
    assert evidence["ref"] == _DB_ID
