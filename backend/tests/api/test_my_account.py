import pytest

from api.mocks import store

ME = "/api/v1/me"
AUTH = "/api/v1/auth"
PASSWORD = "AccountFixture123"


def register_and_login(client, nickname):
    credentials = {"email": f"{nickname}@example.test", "password": PASSWORD}
    assert client.post(f"{AUTH}/signup", json={
        **credentials, "display_name": nickname, "birth_year": 2000, "gender": "female",
    }).status_code == 201
    return login(client, credentials)


def login(client, credentials):
    response = client.post(f"{AUTH}/login", json=credentials)
    assert response.status_code == 200
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["user_id"], data["refresh_token"]


@pytest.mark.parametrize(("method", "path", "body"), [
    ("GET", "/festival-preferences", None),
    ("PUT", "/festival-preferences", {"scenarios": [], "skip": False}),
    ("GET", "/profile", None),
    ("PATCH", "/profile", {"display_name": "닉네임"}),
    ("GET", "/companion-activity?type=posts", None),
    ("DELETE", "", {"password": PASSWORD}),
    ("POST", "/password", {"current_password": PASSWORD, "new_password": "ChangedPass123"}),
])
@pytest.mark.parametrize("real", [False, True])
def test_me_requires_member(client, monkeypatch, method, path, body, real):
    monkeypatch.setenv("AUTH_PROVIDER", "db" if real else "mock")
    response = client.request(method, ME + path, **({"json": body} if body is not None else {}))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert ("X-Mock" not in response.headers) is real


def test_mock_preferences_and_profile(client, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    mine, my_id, refresh = register_and_login(client, "First")
    other, _, _ = register_and_login(client, "Second")
    prefs = f"{ME}/festival-preferences"
    profile = f"{ME}/profile"
    pending = {"scenarios": [], "onboarding_status": "pending", "updated_at": None}
    assert client.get(prefs, headers=mine).json() == pending
    assert client.get(profile, headers=mine).json() == {
        "user_id": my_id, "display_name": "First", "birth_year": 2000,
        "gender": "female", "onboarding_status": "pending",
    }

    response = client.put(prefs, headers=mine, json={"scenarios": ["pet", "solo", "pet"], "skip": False})
    assert response.status_code == 200 and response.headers["X-Mock"] == "true"
    assert response.json()["scenarios"] == ["pet", "solo"]
    assert response.json()["onboarding_status"] == "completed" and response.json()["updated_at"]
    assert client.get(prefs, headers=mine).json() == response.json()
    assert client.get(prefs, headers=other).json() == pending
    assert client.get(profile, headers=mine).json()["onboarding_status"] == "completed"
    for selection in ({"scenarios": ["pet"], "skip": True}, {"scenarios": [], "skip": False}):
        saved = client.put(prefs, headers=mine, json=selection).json()
        assert saved["scenarios"] == [] and saved["onboarding_status"] == "skipped"
    for invalid in ({"scenarios": ["baby"], "skip": False}, {"scenarios": ["solo"] * 6, "skip": False},
                    {"scenarios": [], "skip": "true"}, {"scenarios": []},
                    {"scenarios": [], "skip": False, "user_id": my_id}):
        assert client.put(prefs, headers=mine, json=invalid).status_code == 422

    duplicate = client.patch(profile, headers=mine, json={"display_name": "sECOND"})
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "NICKNAME_TAKEN"
    for invalid in ({"display_name": "x"}, {"display_name": None}, {"role": "admin"}, {"birth_year": 1980}):
        assert client.patch(profile, headers=mine, json=invalid).status_code == 422
    saved = client.patch(profile, headers=mine, json={"display_name": "First New"})
    assert saved.status_code == 200 and saved.json()["display_name"] == "First New"
    assert client.patch(profile, headers=mine, json={}).json() == saved.json()
    token = client.post(f"{AUTH}/refresh", json={"refresh_token": refresh})
    assert token.json()["user"]["display_name"] == "First New"
    assert client.get(profile, headers=other).json()["display_name"] == "Second"
    activity = f"{ME}/companion-activity"
    for kind in ("posts", "applications"):
        assert client.get(activity, params={"type": kind}, headers=mine).json() == {"items": []}
    for params in ({}, {"type": "other"}):
        assert client.get(activity, params=params, headers=mine).status_code == 422


def test_mock_withdrawal_clears_account_sessions_and_owned_data(client, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    mine, my_id, refresh = register_and_login(client, "First")
    other, _, _ = register_and_login(client, "Second")
    credentials = {"email": "First@example.test", "password": PASSWORD}
    second_device, _, second_refresh = login(client, credentials)
    favorite = f"{ME}/favorites/fst_000001"
    for headers in (mine, other):
        assert client.put(favorite, headers=headers).status_code == 201
        assert client.put(f"{ME}/festival-preferences", headers=headers,
                          json={"scenarios": ["pet"], "skip": False}).status_code == 200
    rejected = client.request("DELETE", ME, headers=mine, json={"password": "incorrect"})
    assert rejected.status_code == 403 and rejected.json()["error"]["code"] == "PASSWORD_MISMATCH"
    assert client.get(f"{ME}/profile", headers=mine).status_code == 200

    deleted = client.request("DELETE", ME, headers=mine, json={"password": PASSWORD})
    assert deleted.status_code == 204 and deleted.content == b""
    assert my_id not in store.favorites_by_user and my_id not in store.preferences_by_user
    for headers in (mine, second_device):
        assert client.get(f"{ME}/profile", headers=headers).status_code == 401
    for token in (refresh, second_refresh):
        assert client.post(f"{AUTH}/refresh", json={"refresh_token": token}).status_code == 401
    assert client.post(f"{AUTH}/login", json=credentials).status_code == 401
    assert client.get(f"{ME}/favorites", headers=other).json()["total"] == 1
    assert client.get(f"{ME}/festival-preferences", headers=other).json()["scenarios"] == ["pet"]


@pytest.mark.parametrize("invalid", ["  ", " 가 ", "닉\x00네임", "닉\x85네임", "닉네임\t", " " + "가" * 13])
def test_signup_and_profile_share_nickname_validation(client, monkeypatch, invalid):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    headers, _, _ = register_and_login(client, "Member")
    response = client.post("/api/v1/auth/signup", json={
        "email": "invalid-name@example.test", "password": PASSWORD,
        "display_name": invalid, "birth_year": 2000, "gender": "male",
    })
    changed = client.patch(ME + "/profile", headers=headers, json={"display_name": invalid})
    for rejected in (response, changed):
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"


def test_profile_trims_before_length_and_duplicate_check(client, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    headers, _, _ = register_and_login(client, "First")
    register_and_login(client, "Second")
    duplicate = client.patch(ME + "/profile", headers=headers, json={"display_name": "  sEcOnD  "})
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "NICKNAME_TAKEN"
    name = "가" * 12
    updated = client.patch(ME + "/profile", headers=headers, json={"display_name": f"  {name}  "})
    assert updated.status_code == 200
    assert updated.json()["display_name"] == name


def test_mock_password_change_validates_and_ends_sessions(client, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "mock")
    mine, _, refresh = register_and_login(client, "Changer")
    credentials = {"email": "Changer@example.test", "password": PASSWORD}
    second_device, _, second_refresh = login(client, credentials)
    path = f"{ME}/password"
    new = "ChangedPass123"
    for body in ({"current_password": PASSWORD, "new_password": "short1"},
                 {"current_password": PASSWORD, "new_password": "onlyletters"},
                 {"current_password": PASSWORD, "new_password": PASSWORD},
                 {"current_password": PASSWORD, "new_password": new, "extra": 1}):
        rejected = client.post(path, headers=mine, json=body)
        assert rejected.status_code == 422 and rejected.json()["error"]["code"] == "VALIDATION_ERROR"
    wrong = client.post(path, headers=mine, json={"current_password": "incorrect1", "new_password": new})
    assert wrong.status_code == 403 and wrong.json()["error"]["code"] == "PASSWORD_MISMATCH"
    assert client.get(f"{ME}/profile", headers=mine).status_code == 200

    changed = client.post(path, headers=mine, json={"current_password": PASSWORD, "new_password": new})
    assert changed.status_code == 204 and changed.content == b""
    for headers in (mine, second_device):
        assert client.get(f"{ME}/profile", headers=headers).status_code == 401
    for token in (refresh, second_refresh):
        assert client.post(f"{AUTH}/refresh", json={"refresh_token": token}).status_code == 401
    assert client.post(f"{AUTH}/login", json=credentials).status_code == 401
    fresh, _, _ = login(client, {**credentials, "password": new})
    assert client.get(f"{ME}/profile", headers=fresh).status_code == 200
