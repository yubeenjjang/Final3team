import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from api.mocks.store import users_by_email

AUTH = "/api/v1/auth"
USER = {
    "email": "abc@example.com",
    "password": "example123",
    "display_name": "Abc",
    "birth_year": 2000,
    "gender": "male",
}


def _signup(client: TestClient, **fields: object) -> dict:
    response = client.post(f"{AUTH}/signup", json={**USER, **fields})
    assert response.status_code == 201
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    assert str(UUID(body["user_id"])) == body["user_id"]
    return body


def _tokens(response: Response) -> dict:
    assert response.status_code == 200
    assert response.headers["X-Mock"] == "true"
    body = response.json()
    assert body["is_mock"] is True
    assert re.fullmatch(r"mock_at_[0-9A-Za-z]{32}", body["access_token"])
    assert re.fullmatch(r"mock_rt_[0-9A-Za-z]{32}", body["refresh_token"])
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    assert datetime.fromisoformat(body["refresh_expires_at"]).tzinfo is not None
    assert body["user"]["role"] == "user"
    return body


def _login(client: TestClient, email: str = "ABC@example.com") -> dict:
    return _tokens(client.post(f"{AUTH}/login", json={"email": email, "password": USER["password"]}))


def test_R16_signup_and_duplicates(client: TestClient) -> None:
    signup = _signup(client, display_name="  Abc  ")
    assert signup == {"user_id": signup["user_id"], "display_name": "Abc", "is_mock": True}
    assert users_by_email["abc@example.com"].salt
    assert users_by_email["abc@example.com"].password_hash != USER["password"].encode()

    email_response = client.post(f"{AUTH}/signup", json={**USER, "email": "AbC@ExAmPlE.com"})
    assert email_response.status_code == 409
    assert email_response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    nick_response = client.post(
        f"{AUTH}/signup", json={**USER, "email": "other@example.com", "display_name": "abc"}
    )
    assert nick_response.status_code == 409
    assert nick_response.json()["error"]["code"] == "NICKNAME_TAKEN"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "bad.example.com"),
        ("email", "a@" + "x." * 126 + "com"),
        ("display_name", " A "),
        ("display_name", "a" * 13),
        ("birth_year", 2100),
        ("birth_year", 1899),
        ("password", "12345678"),
        ("password", "abcdefgh"),
        ("password", "abc123"),
        ("password", "a" * 64 + "1"),
        ("gender", "unknown"),
    ],
)
def test_R16_signup_validation(client: TestClient, field: str, value: object) -> None:
    response = client.post(f"{AUTH}/signup", json={**USER, field: value})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["message"]


def test_R16_login_success_and_invalid_credentials(client: TestClient) -> None:
    signup = _signup(client)
    tokens = _login(client)
    assert tokens["user"] == {"user_id": signup["user_id"], "display_name": "Abc", "role": "user"}

    errors = []
    for email in ("abc@example.com", "missing@example.com"):
        response = client.post(
            f"{AUTH}/login", json={"email": email, "password": "wrong123"}, headers={"X-Request-ID": "login-test"}
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"
        errors.append(response.json())
    assert errors[0] == errors[1]


def test_R16_refresh_ttl_14_days(client: TestClient) -> None:
    _signup(client)
    login_at = datetime.now(timezone.utc)
    tokens = _login(client)
    refresh_expires_at = datetime.fromisoformat(tokens["refresh_expires_at"])
    assert timedelta(days=13.9) <= refresh_expires_at - login_at <= timedelta(days=14.1)


def test_R16_refresh_rotation_and_reuse_revokes_all_user_refresh_tokens(client: TestClient) -> None:
    _signup(client)
    first = _login(client)
    concurrent_login = _login(client)
    _signup(client, email="other@example.com", display_name="Other")
    other_login = _login(client, "other@example.com")

    def refresh(token: str) -> Response:
        return client.post(f"{AUTH}/refresh", json={"refresh_token": token})

    unknown = refresh("unknown")
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "REFRESH_INVALID"

    renewed = _tokens(refresh(first["refresh_token"]))
    assert renewed["refresh_token"] != first["refresh_token"]
    assert renewed["access_token"] != first["access_token"]
    assert renewed["user"] == first["user"]
    reused = refresh(first["refresh_token"])
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "REFRESH_REUSED"
    assert refresh(renewed["refresh_token"]).status_code == 401
    assert refresh(concurrent_login["refresh_token"]).status_code == 401
    _tokens(refresh(other_login["refresh_token"]))


def test_R16_logout(client: TestClient) -> None:
    _signup(client)
    tokens = _login(client)
    body = {"refresh_token": tokens["refresh_token"]}
    for headers in ({}, {"Authorization": "Bearer unknown"}):
        response = client.post(f"{AUTH}/logout", json=body, headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.post(f"{AUTH}/logout", json=body, headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["X-Mock"] == "true"

    repeated = client.post(f"{AUTH}/logout", json=body, headers=headers)
    assert repeated.status_code == 401
    assert repeated.json()["error"]["code"] == "UNAUTHORIZED"
    assert client.post(f"{AUTH}/refresh", json=body).status_code == 401
