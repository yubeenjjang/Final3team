from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from api import deps
from api.auth import service, state, tokens
from api.errors import ApiError

AUTH = "/api/v1/auth"
SIGNUP = {
    "email": "Person@example.test", "password": "Example-Test123",
    "display_name": "Tester", "birth_year": 2000, "gender": "female",
}
LOGIN = {name: SIGNUP[name] for name in ("email", "password")}
ISSUER = "auth-tests"


@pytest.fixture
def db_mode(monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "db")
    monkeypatch.setenv("JWT_SECRET", "fixture-auth-signing-value-for-offline-tests-only")
    monkeypatch.setenv("JWT_ISSUER", ISSUER)
    for key in ("ACCESS_JWT_TTL_MIN", "REFRESH_TTL_DAYS", "AUTH_RATE_LIMIT_PER_MIN", "REFRESH_LOCK_TTL_S"):
        monkeypatch.delenv(key, raising=False)
    memory = state.MemoryAuthState()
    monkeypatch.setattr(state, "_auth_state", memory)
    return memory


def use_db_calls(monkeypatch, *sessions):
    remaining = iter(sessions)
    committed = []

    @contextmanager
    def session():
        db = next(remaining)
        yield db
        committed.append(db)

    monkeypatch.setattr(service, "service_db_session", session)
    return committed


def test_password_argon2id_salts_and_verifies():
    password = SIGNUP["password"]
    first = tokens.hash_password(password)
    second = tokens.hash_password(password)
    assert first.startswith("$argon2id$") and second.startswith("$argon2id$")
    assert first != second
    assert tokens.password_matches(password, first)
    assert not tokens.password_matches("different", first)
    assert not tokens.password_matches(password, None)
    assert not tokens.password_matches(password, "!")


def test_access_jwt_signature_issuer_claims_and_expiry(db_mode, monkeypatch):
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    access = tokens.issue_access_token(user_id, "operator", now, 1800)
    claims = tokens.read_access_token(f"bearer {access}")
    assert claims.user_id == user_id
    assert claims.expires_at == int(now.timestamp()) + 1800
    key, _ = tokens._jwt_settings()
    decoded = jwt.decode(access, key, algorithms=["HS256"], issuer=ISSUER)
    assert decoded["role"] == "operator"
    assert decoded["jti"] == claims.jti
    assert decoded["exp"] - decoded["iat"] == 1800

    expired = tokens.issue_access_token(user_id, "user", now - timedelta(hours=1), 1800)
    other_algorithm = jwt.encode(decoded, key, algorithm="HS384")
    missing_jti = jwt.encode({name: value for name, value in decoded.items() if name != "jti"}, key)
    for invalid in (expired, other_algorithm, missing_jti, access[:-6] + "broken"):
        with pytest.raises(ApiError, match="액세스 토큰") as error:
            tokens.read_access_token(f"Bearer {invalid}")
        assert error.value.status == 401
    monkeypatch.setenv("JWT_ISSUER", "wrong-issuer")
    with pytest.raises(ApiError):
        tokens.read_access_token(f"Bearer {access}")


def test_db_signup_validation_hash_and_duplicates(client, db_mode, monkeypatch):
    valid_db, duplicate_email, duplicate_nickname = (Mock(spec=Session) for _ in range(3))
    valid_db.scalar.return_value = False
    duplicate_email.scalar.return_value = True
    duplicate_nickname.scalar.return_value = False
    duplicate_nickname.execute.side_effect = [
        None, IntegrityError(None, None, SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_profiles_nickname"))),
    ]
    committed = use_db_calls(monkeypatch, valid_db, duplicate_email, duplicate_nickname)

    invalid = client.post(f"{AUTH}/signup", json={**SIGNUP, "password": "invalid"})
    assert invalid.status_code == 422 and "X-Mock" not in invalid.headers
    response = client.post(f"{AUTH}/signup", json=SIGNUP)
    assert response.status_code == 201 and "X-Mock" not in response.headers
    assert response.json()["is_mock"] is False
    user, profile = [call.args[1] for call in valid_db.execute.call_args_list]
    assert user["email"] == SIGNUP["email"].lower()
    assert user["password_hash"].startswith("$argon2id$")
    assert str(user["user_id"]) == response.json()["user_id"]
    assert user["user_id"] == profile["user_id"]
    assert profile["birth_year"] == SIGNUP["birth_year"] and profile["gender"] == SIGNUP["gender"]

    for code in ("EMAIL_ALREADY_EXISTS", "NICKNAME_TAKEN"):
        duplicate = client.post(f"{AUTH}/signup", json=SIGNUP)
        assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == code
    assert committed == [valid_db]


def test_db_login_success_and_invalid_credentials(client, db_mode, monkeypatch):
    user_id = uuid4()
    digest = tokens.hash_password(LOGIN["password"])
    active = SimpleNamespace(user_id=user_id, password_hash=digest, status="active")
    lookup, write = Mock(spec=Session), Mock(spec=Session)
    lookup.execute.return_value.all.side_effect = [
        [active], [], [SimpleNamespace(user_id=user_id, password_hash=digest, status="disabled")], [active],
    ]
    result = Mock()
    result.scalar_one_or_none.return_value = user_id
    result.one.return_value = SimpleNamespace(display_name="Tester", role="user")
    write.execute.return_value = result
    committed = use_db_calls(monkeypatch, lookup, lookup, lookup, lookup, write)

    failures = [
        client.post(f"{AUTH}/login", json={**LOGIN, "password": "wrong123"}, headers={"X-Request-ID": "login-test"}),
        client.post(f"{AUTH}/login", json={**LOGIN, "email": "unknown@example.test"}, headers={"X-Request-ID": "login-test"}),
    ]
    assert all(error.status_code == 401 and "X-Mock" not in error.headers for error in failures)
    assert failures[0].json() == failures[1].json()
    assert failures[0].json()["error"]["code"] == "INVALID_CREDENTIALS"
    disabled = client.post(f"{AUTH}/login", json=LOGIN)
    assert disabled.status_code == 403 and disabled.json()["error"]["code"] == "ACCOUNT_DISABLED"

    response = client.post(f"{AUTH}/login", json=LOGIN)
    assert response.status_code == 200 and "X-Mock" not in response.headers
    data = response.json()
    assert data["user"] == {"user_id": str(user_id), "display_name": "Tester", "role": "user"}
    assert data["expires_in"] == 1800 and data["token_type"] == "bearer" and data["is_mock"] is False
    login_update, _, refresh_insert = [call.args[1] for call in write.execute.call_args_list]
    assert refresh_insert["token_hash"] == tokens.refresh_hash(data["refresh_token"])
    assert refresh_insert["expires_at"] - login_update["now"] == timedelta(days=14)
    assert datetime.fromisoformat(data["refresh_expires_at"]).utcoffset() == timedelta(hours=9)
    assert committed[-1] is write


def test_db_refresh_rotates_and_commits_reuse_before_401(client, db_mode, monkeypatch):
    user_id = uuid4()
    token_id = "rt_0123456789"
    now = datetime.now(timezone.utc)
    old = "initial-fixture-refresh"
    lookup, rotate, reuse = (Mock(spec=Session) for _ in range(3))
    lookup.execute.return_value.one_or_none.return_value = SimpleNamespace(token_id=token_id, user_id=user_id)
    rotate.scalar.side_effect = [True, "active"]
    rotate.execute.return_value.one_or_none.return_value = SimpleNamespace(
        expires_at=now + timedelta(days=14), revoked_at=None,
    )
    rotate.execute.return_value.one.return_value = SimpleNamespace(display_name="Tester", role="user")
    reuse.scalar.side_effect = [True, "active"]
    reuse.execute.return_value.one_or_none.return_value = SimpleNamespace(
        expires_at=now + timedelta(days=14), revoked_at=now,
    )
    locked_elsewhere = Mock(spec=Session)
    locked_elsewhere.scalar.return_value = False
    committed = use_db_calls(monkeypatch, lookup, rotate, lookup, reuse, lookup, lookup, locked_elsewhere)

    rotated = client.post(f"{AUTH}/refresh", json={"refresh_token": old})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != old
    assert rotate.execute.call_args_list[1].args[1]["token_id"] == token_id
    assert rotate.execute.call_args_list[-1].args[1]["token_hash"] == tokens.refresh_hash(rotated.json()["refresh_token"])
    again = client.post(f"{AUTH}/refresh", json={"refresh_token": old})
    assert again.status_code == 401 and again.json()["error"]["code"] == "REFRESH_REUSED"
    update, values = reuse.execute.call_args.args
    assert "WHERE user_id = :user_id AND revoked_at IS NULL" in str(update)
    assert values["user_id"] == user_id
    assert committed == [lookup, rotate, lookup, reuse]

    assert db_mode.lock_refresh(token_id, "another-request", 5)
    busy = client.post(f"{AUTH}/refresh", json={"refresh_token": old})
    assert busy.status_code == 409 and busy.json()["error"]["code"] == "REFRESH_IN_PROGRESS"
    db_mode.unlock_refresh(token_id, "another-request")
    busy = client.post(f"{AUTH}/refresh", json={"refresh_token": old})
    assert busy.status_code == 409 and locked_elsewhere.execute.call_count == 0


def test_db_refresh_rejects_unknown_and_expired(client, db_mode, monkeypatch):
    missing, lookup, expired = (Mock(spec=Session) for _ in range(3))
    missing.execute.return_value.one_or_none.return_value = None
    lookup.execute.return_value.one_or_none.return_value = SimpleNamespace(token_id="rt_0123456789", user_id=uuid4())
    expired.scalar.side_effect = [True, "active"]
    expired.execute.return_value.one_or_none.return_value = SimpleNamespace(
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1), revoked_at=None,
    )
    use_db_calls(monkeypatch, missing, lookup, expired)

    for raw in ("unknown", "expired"):
        response = client.post(f"{AUTH}/refresh", json={"refresh_token": raw})
        assert response.status_code == 401 and response.json()["error"]["code"] == "REFRESH_INVALID"
    assert expired.execute.call_count == 1


def use_user_dependency(monkeypatch, user_id, role="user"):
    caller_id = user_id

    async def scalar(statement, params):
        assert params["user_id"] == caller_id
        return role

    db = SimpleNamespace(scalar=scalar)

    @asynccontextmanager
    async def rls_session(user_id=None):
        assert user_id == caller_id
        yield db

    monkeypatch.setattr(deps, "user_db_session", rls_session)
    monkeypatch.setattr(service, "account_is_active", lambda caller: caller == user_id)


def test_db_logout_revokes_owned_refresh_and_access(client, db_mode, monkeypatch):
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    header = {"Authorization": f"Bearer {tokens.issue_access_token(user_id, 'user', now, 1800)}"}
    claims = tokens.read_access_token(header["Authorization"])
    use_user_dependency(monkeypatch, user_id)
    missing, write = Mock(spec=Session), Mock(spec=Session)
    for db in (missing, write):
        db.scalar.return_value = "active"
    missing.execute.return_value.scalar_one_or_none.return_value = None
    write.execute.return_value.scalar_one_or_none.return_value = "rt_0123456789"
    committed = use_db_calls(monkeypatch, missing, write, write)

    unknown = client.post(f"{AUTH}/logout", headers=header, json={"refresh_token": "other"})
    assert unknown.status_code == 401 and not db_mode.is_revoked(claims.jti)
    with monkeypatch.context() as failure:
        failure.setattr(db_mode, "revoke", Mock(side_effect=state.AuthStateUnavailable()))
        unavailable = client.post(f"{AUTH}/logout", headers=header, json={"refresh_token": "owned"})
        assert unavailable.status_code == 503 and unavailable.json()["error"]["code"] == "AUTH_CHECK_UNAVAILABLE"
        assert committed == [write]
    response = client.post(f"{AUTH}/logout", headers=header, json={"refresh_token": "owned"})
    assert response.status_code == 204 and not response.content and "X-Mock" not in response.headers
    assert committed == [write, write]
    assert write.execute.call_args.args[1]["user_id"] == user_id
    assert write.execute.call_args.args[1]["digest"] == tokens.refresh_hash("owned")
    assert db_mode.is_revoked(claims.jti)
    assert client.post(f"{AUTH}/logout", headers=header, json={"refresh_token": "owned"}).status_code == 401


def test_login_limit_is_per_ip_and_resets_each_minute(client, db_mode, monkeypatch):
    from api.main import app

    now = datetime(2026, 11, 24, 8, 30, 10, tzinfo=timezone.utc)
    clock = Mock()
    clock.now.return_value = now
    monkeypatch.setattr(state, "datetime", clock)
    login = Mock(side_effect=ApiError(401, "INVALID_CREDENTIALS", "인증 실패"))
    monkeypatch.setattr(service, "login", login)
    malformed = client.post(f"{AUTH}/login", content="{", headers={"Content-Type": "application/json"})
    assert malformed.status_code == 422
    for _ in range(9):
        assert client.post(f"{AUTH}/login", json=LOGIN).status_code == 401
    limited = client.post(f"{AUTH}/login", json=LOGIN)
    assert limited.status_code == 429 and limited.json()["error"]["code"] == "RATE_LIMITED"
    assert limited.headers["Retry-After"] == "50"
    assert login.call_count == 9

    with TestClient(app, client=("127.0.0.2", 50000)) as other_client:
        assert other_client.post(f"{AUTH}/login", json=LOGIN).status_code == 401
    clock.now.return_value = now + timedelta(minutes=1)
    assert client.post(f"{AUTH}/login", json=LOGIN).status_code == 401


def test_state_outage_allows_only_protected_reads_and_uses_database_role(db_mode, monkeypatch, client):
    user_id = uuid4()
    use_user_dependency(monkeypatch, user_id, role="operator")
    header = {"Authorization": f"Bearer {tokens.issue_access_token(user_id, 'admin', datetime.now(timezone.utc), 1800)}"}
    monkeypatch.setattr(db_mode, "is_revoked", Mock(side_effect=state.AuthStateUnavailable()))
    monkeypatch.setattr(db_mode, "count_login", Mock(side_effect=state.AuthStateUnavailable()))
    test_app = FastAPI()
    test_app.add_exception_handler(ApiError, lambda _, exc: JSONResponse({"code": exc.code}, exc.status))

    @test_app.get("/read")
    async def read(user: Annotated[deps.CurrentUser | None, Depends(deps.get_current_user)]):
        return user.role if user else None

    @test_app.post("/write")
    async def write(db: Annotated[AsyncSession, Depends(deps.get_user_db)]):
        return True

    @test_app.get("/api/v1/admin/read")
    async def admin(user: Annotated[deps.CurrentUser, Depends(deps.require_role("admin"))]):
        return True

    with TestClient(test_app) as test_client:
        assert test_client.get("/read", headers=header).json() == "operator"
        assert test_client.get("/read").json() is None
        for response in (test_client.post("/write", headers=header),
                         test_client.get("/api/v1/admin/read", headers=header)):
            assert response.status_code == 503 and response.json()["code"] == "AUTH_CHECK_UNAVAILABLE"
        monkeypatch.setattr(db_mode, "is_revoked", Mock(return_value=False))
        assert test_client.get("/api/v1/admin/read", headers=header).status_code == 403

    login = client.post(f"{AUTH}/login", json=LOGIN)
    assert login.status_code == 503 and login.json()["error"]["code"] == "AUTH_CHECK_UNAVAILABLE"


def test_memory_revocation_and_lock_ttl(db_mode, monkeypatch):
    clock = Mock(return_value=100.0)
    monkeypatch.setattr(state, "monotonic", clock)
    db_mode.revoke("jti", 10)
    assert db_mode.lock_refresh("rt_test", "old-owner", 5)
    clock.return_value = 105.0
    assert db_mode.lock_refresh("rt_test", "new-owner", 5)
    db_mode.unlock_refresh("rt_test", "old-owner")
    assert not db_mode.lock_refresh("rt_test", "third-owner", 5)
    assert db_mode.is_revoked("jti")
    clock.return_value = 110.0
    assert not db_mode.is_revoked("jti")
