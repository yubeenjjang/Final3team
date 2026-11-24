import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

from api.errors import ApiError

_PASSWORD_HASHER = PasswordHasher(type=Type.ID)


def uses_auth_db() -> bool:
    return os.environ.get("AUTH_PROVIDER") == "db"


def positive_setting(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = 0
    if value <= 0:
        raise ValueError(f"{name}에는 양의 정수가 필요합니다.")
    return value


def _jwt_settings() -> tuple[bytes, str]:
    key = os.environ.get("JWT_SECRET", "").encode()
    if len(key.strip()) < 32:
        raise ValueError("JWT_SECRET에 32바이트 이상의 비밀값이 필요합니다.")
    return key, os.environ.get("JWT_ISSUER", "noldaga-api")


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(32))


def password_matches(password: str, encoded: str | None) -> bool:
    # 미가입·탈퇴 계정도 정상 계정과 같은 비용으로 검증합니다.
    is_argon2id = bool(encoded and encoded.startswith("$argon2id$"))
    try:
        return _PASSWORD_HASHER.verify(encoded if is_argon2id else _dummy_hash(), password) and is_argon2id
    except (InvalidHashError, VerificationError):
        return False


def refresh_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def login_ip_hash(ip: str) -> str:
    key, _ = _jwt_settings()
    return hmac.digest(key, b"auth:ip:" + ip.encode(), "sha256").hex()


def unauthorized() -> ApiError:
    return ApiError(401, "UNAUTHORIZED", "유효한 액세스 토큰을 보내 주세요.")


@dataclass(frozen=True)
class AccessClaims:
    user_id: UUID
    jti: str
    expires_at: int


def issue_access_token(user_id: UUID, role: str, now: datetime, duration: int) -> str:
    key, issuer = _jwt_settings()
    issued_at = int(now.timestamp())
    return jwt.encode({
        "iss": issuer,
        "sub": str(user_id),
        "role": role,
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": issued_at + duration,
    }, key, algorithm="HS256")


def read_access_token(authorization: str) -> AccessClaims:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise unauthorized()
    key, issuer = _jwt_settings()
    try:
        claims = jwt.decode(token, key, algorithms=["HS256"], issuer=issuer, options={
            "require": ["iss", "sub", "role", "jti", "exp"],
        })
        user_id = UUID(claims["sub"])
        jti = claims["jti"]
        if not isinstance(jti, str) or not jti:
            raise ValueError
        if claims["role"] not in ("user", "operator", "admin") or type(claims["exp"]) is not int:
            raise ValueError
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise unauthorized() from None
    return AccessClaims(user_id, jti, claims["exp"])
