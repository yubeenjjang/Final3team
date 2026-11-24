"""사용자 인증과 요청용 RLS 세션 의존성."""

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.auth import service, state
from api.auth.tokens import AccessClaims, read_access_token, unauthorized, uses_auth_db
from api.errors import ApiError
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


async def get_current_user(auth: AuthenticatedSession) -> CurrentUser | None:
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
