import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from api.errors import ApiError
from api.mocks.store import (
    AccessSession,
    MockUser,
    RefreshSession,
    access_sessions,
    auth_lock,
    refresh_sessions,
    retired_refresh_tokens,
    user_nicknames,
    users_by_email,
)
from api.schemas.auth import LoginRequest, SignupRequest

_ACCESS_DURATION = 1800
_REFRESH_DURATION = timedelta(days=14)


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)


def signup(request: SignupRequest) -> dict[str, object]:
    nickname = request.display_name.casefold()
    with auth_lock:
        if request.email in users_by_email:
            raise ApiError(409, "EMAIL_ALREADY_EXISTS", "이미 가입한 이메일입니다.")
        if nickname in user_nicknames:
            raise ApiError(409, "NICKNAME_TAKEN", "이미 사용 중인 닉네임입니다.")
        salt = secrets.token_bytes(16)
        user = MockUser(
            user_id=str(uuid4()),
            display_name=request.display_name,
            salt=salt,
            password_hash=_password_hash(request.password.get_secret_value(), salt),
        )
        users_by_email[request.email] = user
        user_nicknames.add(nickname)
    return {"user_id": user.user_id, "display_name": user.display_name, "is_mock": True}


def login(request: LoginRequest) -> dict[str, object]:
    with auth_lock:
        user = users_by_email.get(request.email.lower())
        salt = user.salt if user is not None else bytes(16)
        digest = _password_hash(request.password.get_secret_value(), salt)
        if user is None or not secrets.compare_digest(user.password_hash, digest):
            raise ApiError(401, "INVALID_CREDENTIALS", "이메일이나 비밀번호를 확인해 주세요.")
        return _issue_tokens(user, datetime.now(timezone.utc))


def _issue_tokens(user: MockUser, now: datetime) -> dict[str, object]:
    access_token = "mock_at_" + secrets.token_hex(16)
    refresh_token = "mock_rt_" + secrets.token_hex(16)
    refresh_expires_at = now + _REFRESH_DURATION
    access_sessions[access_token] = AccessSession(
        user.user_id, now + timedelta(seconds=_ACCESS_DURATION)
    )
    refresh_sessions[refresh_token] = RefreshSession(user, refresh_expires_at)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": _ACCESS_DURATION,
        "refresh_token": refresh_token,
        "refresh_expires_at": refresh_expires_at.isoformat(),
        "user": {"user_id": user.user_id, "display_name": user.display_name, "role": "user"},
        "is_mock": True,
    }


def _retire_refresh(token: str, user_id: str) -> None:
    del refresh_sessions[token]
    retired_refresh_tokens[token] = user_id


def refresh(token: str) -> dict[str, object]:
    with auth_lock:
        owner = retired_refresh_tokens.get(token)
        if owner is not None:
            for active_token, session in tuple(refresh_sessions.items()):
                if session.user.user_id == owner:
                    _retire_refresh(active_token, owner)
            raise ApiError(401, "REFRESH_REUSED", "이미 폐기된 인증 갱신 토큰입니다.")

        now = datetime.now(timezone.utc)
        session = refresh_sessions.get(token)
        if session is None or session.expires_at <= now:
            raise ApiError(401, "REFRESH_INVALID", "유효한 인증 갱신 토큰을 보내 주세요.")
        _retire_refresh(token, session.user.user_id)
        return _issue_tokens(session.user, now)


def logout(authorization: str | None, refresh_token: str) -> None:
    scheme, _, access_token = (authorization or "").partition(" ")
    with auth_lock:
        session = access_sessions.get(access_token)
        now = datetime.now(timezone.utc)
        if scheme.lower() != "bearer" or session is None or session.expires_at <= now:
            raise ApiError(401, "UNAUTHORIZED", "유효한 액세스 토큰을 보내 주세요.")
        del access_sessions[access_token]
        refresh_session = refresh_sessions.get(refresh_token)
        if refresh_session is not None and refresh_session.user.user_id == session.user_id:
            _retire_refresh(refresh_token, session.user_id)
