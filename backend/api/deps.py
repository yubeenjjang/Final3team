"""사용자 인증과 요청용 RLS 세션 의존성."""

import os
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.auth import service, state
from api.auth.tokens import AccessClaims, read_access_token, unauthorized, uses_auth_db
from api.errors import ApiError
from api.mocks.store import auth_lock
from api.request_logs import (
    ADMIN_REPORTS_PATH, ADMIN_REVIEW_PATH, admin_festival_endpoint, admin_notice_endpoint, admin_rag_document_endpoint,
)
from api.services.mock_auth import authenticated_access
from shared.db.session import user_db_session

Authorization = Annotated[str | None, Header()]


@dataclass(frozen=True)
class CurrentUser:
    claims: AccessClaims
    role: str
    revocation_checked: bool


async def _authenticated_session(
    request: Request, authorization: Authorization = None,
) -> AsyncIterator[tuple[CurrentUser, AsyncSession] | None]:
    if not uses_auth_db() or authorization is None:
        yield None
        return

    claims = read_access_token(authorization)
    revocation_checked = True
    try:
        revoked = await run_in_threadpool(state.get_auth_state().is_revoked, claims.jti)
    except state.AuthStateUnavailable:
        path = getattr(request.scope.get("route"), "path", request.url.path)
        is_admin = path == "/api/v1/admin" or path.startswith("/api/v1/admin/")
        if request.method not in {"GET", "HEAD", "OPTIONS"} or is_admin:
            raise state.auth_check_unavailable() from None
        revocation_checked = False
    else:
        if revoked:
            raise unauthorized()

    if not await run_in_threadpool(service.account_is_active, claims.user_id):
        raise unauthorized()
    # DB-19: 검증된 JWT sub를 공통 세션에 전달해 RLS의 app.user_id를 설정합니다.
    async with user_db_session(user_id=claims.user_id) as db:
        role = await db.scalar(text("SELECT role FROM public.profiles WHERE user_id = :user_id"),
                               {"user_id": claims.user_id})
        if role is None:
            raise unauthorized()
        yield CurrentUser(claims, role, revocation_checked), db


AuthenticatedSession = Annotated[tuple[CurrentUser, AsyncSession] | None,
                                 Depends(_authenticated_session, scope="function")]


_MOCK_OPERATOR_TOKENS = {
    ADMIN_REVIEW_PATH: "MOCK_ADMIN_REVIEW_TOKEN",
    ADMIN_REPORTS_PATH: "MOCK_ADMIN_REPORTS_TOKEN",
}


def _mock_operator(authorization: str | None, setting: str) -> CurrentUser:
    configured = os.environ.get(setting, "").encode()
    scheme, _, token = (authorization or "").partition(" ")
    if len(configured) >= 32 and scheme.lower() == "bearer" and secrets.compare_digest(configured, token.encode()):
        return CurrentUser(AccessClaims(UUID(int=0), "mock-admin-review", 0), "operator", True)
    with auth_lock:
        _, session = authenticated_access(authorization, datetime.now(timezone.utc))
    return CurrentUser(
        AccessClaims(UUID(session.user_id), "mock-user", int(session.expires_at.timestamp())), "user", True,
    )


def _mock_admin_user(authorization: str | None) -> CurrentUser:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer":
        configured = os.environ.get("MOCK_ADMIN_FESTIVALS_TOKEN", "").encode()
        if len(configured) >= 32 and secrets.compare_digest(configured, token.encode()):
            return CurrentUser(AccessClaims(UUID(int=1), "mock-admin-festivals", 0), "admin", True)
        configured = os.environ.get("MOCK_ADMIN_REVIEW_TOKEN", "").encode()
        if len(configured) >= 32 and secrets.compare_digest(configured, token.encode()):
            return CurrentUser(AccessClaims(UUID(int=0), "mock-admin-review", 0), "operator", True)
    with auth_lock:
        _, session = authenticated_access(authorization, datetime.now(timezone.utc))
    return CurrentUser(
        AccessClaims(UUID(session.user_id), "mock-user", int(session.expires_at.timestamp())), "user", True,
    )


async def get_current_user(
    auth: AuthenticatedSession, request: Request, authorization: Authorization = None,
) -> CurrentUser | None:
    if not uses_auth_db() and admin_festival_endpoint(request.url.path):
        return await run_in_threadpool(_mock_admin_user, authorization)
    setting = _MOCK_OPERATOR_TOKENS.get(request.url.path.rstrip("/"))
    if setting is None and (
        admin_notice_endpoint(request.url.path) is not None or admin_rag_document_endpoint(request.url.path) is not None
    ):
        setting = _MOCK_OPERATOR_TOKENS[ADMIN_REVIEW_PATH]
    if not uses_auth_db() and setting is not None:
        return await run_in_threadpool(_mock_operator, authorization, setting)
    return auth[0] if auth else None


async def get_user_db(auth: AuthenticatedSession) -> AsyncSession:
    if auth is None:
        raise unauthorized()
    return auth[1]


def require_role(*roles: str) -> Callable[..., Awaitable[CurrentUser]]:
    async def check(user: Annotated[CurrentUser | None, Depends(get_current_user)]) -> CurrentUser:
        if user is None:
            raise unauthorized()
        if not user.revocation_checked and any(role in {"admin", "operator"} for role in roles):
            raise state.auth_check_unavailable()
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "요청에 필요한 권한이 없습니다.")
        return user

    return check
