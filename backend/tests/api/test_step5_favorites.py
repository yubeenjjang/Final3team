from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from api.services import mock_favorites

AUTH = "/api/v1/auth"
FAVORITES = "/api/v1/me/favorites"


def _register_and_login(client: TestClient, display_name: str) -> tuple[dict[str, str], str]:
    credentials = {"email": f"{display_name}@example.com", "password": "example123"}
    signup = client.post(
        f"{AUTH}/signup",
        json={**credentials, "display_name": display_name, "birth_year": 2000, "gender": "male"},
    )
    assert signup.status_code == 201
    login = client.post(f"{AUTH}/login", json=credentials)
    assert login.status_code == 200
    tokens = login.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}, tokens["refresh_token"]


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_R22_access_token_required(client: TestClient, method: str) -> None:
    path = FAVORITES if method == "GET" else f"{FAVORITES}/fst_000001"
    for headers in ({}, {"Authorization": "Bearer mock_at_unknown"}):
        response = client.request(method, path, headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_R22_save_list_isolate_and_delete(client: TestClient) -> None:
    first_user, _ = _register_and_login(client, "First")
    second_user, _ = _register_and_login(client, "Second")
    path = f"{FAVORITES}/fst_000001"

    created = client.put(path, headers=first_user)
    assert created.status_code == 201
    assert created.headers["X-Mock"] == "true"
    saved = created.json()
    assert saved == {"festival_id": "fst_000001", "saved_at": saved["saved_at"], "is_mock": True}
    assert datetime.fromisoformat(saved["saved_at"]).tzinfo is not None
    duplicate = client.put(path, headers=first_user)
    assert duplicate.status_code == 200
    assert duplicate.json() == saved

    listed = client.get(FAVORITES, headers=first_user)
    assert listed.status_code == 200
    assert listed.json() == {
        "items": [{
            "festival_id": "fst_000001",
            "name": "광화문 겨울빛 축제",
            "region_code": "SEOUL",
            "start_date": "2026-11-20",
            "end_date": "2026-12-31",
            "event_status": "ongoing",
            "thumbnail_url": listed.json()["items"][0]["thumbnail_url"],
            "saved_at": saved["saved_at"],
        }],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "is_mock": True,
    }
    other_list = client.get(FAVORITES, headers=second_user)
    assert other_list.status_code == 200
    assert other_list.json()["total"] == 0
    assert other_list.json()["items"] == []
    assert client.delete(path, headers=second_user).status_code == 204
    assert client.get(FAVORITES, headers=first_user).json()["total"] == 1

    for _ in range(2):
        deleted = client.delete(path, headers=first_user)
        assert deleted.status_code == 204
        assert deleted.content == b""
    after_delete = client.get(FAVORITES, headers=first_user)
    assert after_delete.status_code == 200
    assert after_delete.json()["total"] == 0


def test_R22_missing_invalid_festival_and_logout(client: TestClient) -> None:
    headers, refresh_token = _register_and_login(client, "First")
    unknown = client.put(f"{FAVORITES}/fst_999999", headers=headers)
    assert unknown.status_code == 404
    assert unknown.json()["error"]["code"] == "FESTIVAL_NOT_FOUND"
    assert client.delete(f"{FAVORITES}/fst_999999", headers=headers).status_code == 204
    for method in ("PUT", "DELETE"):
        invalid = client.request(method, f"{FAVORITES}/bad", headers=headers)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    logout = client.post(f"{AUTH}/logout", headers=headers, json={"refresh_token": refresh_token})
    assert logout.status_code == 204
    expired = client.get(FAVORITES, headers=headers)
    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "UNAUTHORIZED"


def test_R22_sort_and_paginate_same_second(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, _ = _register_and_login(client, "First")
    now = datetime.now().astimezone()

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None) -> datetime:
            return now.astimezone(tz)

    monkeypatch.setattr(mock_favorites, "datetime", FixedDateTime)
    timestamps = set()
    for festival_id in ("fst_000003", "fst_000001", "fst_000006"):
        response = client.put(f"{FAVORITES}/{festival_id}", headers=headers)
        assert response.status_code == 201
        timestamps.add(response.json()["saved_at"])
    assert len(timestamps) == 1

    latest = client.get(FAVORITES, headers=headers)
    assert latest.status_code == 200
    assert [item["festival_id"] for item in latest.json()["items"]] == [
        "fst_000006", "fst_000001", "fst_000003"
    ]

    by_date = client.get(FAVORITES, headers=headers, params={"sort": "start_date"})
    assert by_date.status_code == 200
    assert [item["festival_id"] for item in by_date.json()["items"]] == [
        "fst_000003", "fst_000001", "fst_000006"
    ]

    page = client.get(FAVORITES, headers=headers, params={"page": 2, "page_size": 1})
    assert page.status_code == 200
    body = page.json()
    assert (body["total"], body["page"], body["page_size"]) == (3, 2, 1)
    assert [item["festival_id"] for item in body["items"]] == ["fst_000001"]

    for params in ({"page": "0"}, {"page_size": "0"}, {"page_size": "101"}, {"sort": "name"}):
        invalid = client.get(FAVORITES, headers=headers, params=params)
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
