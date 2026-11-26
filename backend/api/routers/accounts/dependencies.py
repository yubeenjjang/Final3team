from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from api.auth.service import account_is_active
from api.auth.tokens import unauthorized, uses_auth_db
from api.deps import AuthenticatedSession, Authorization, CurrentUser, get_current_user
from api.mocks.store import auth_lock
from api.services.mock_auth import authenticated_access


def _check_mock_access(authorization: str | None) -> None:
    with auth_lock:
        authenticated_access(authorization, datetime.now(timezone.utc))


async def _get_me_session(
    request: Request,
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    auth: AuthenticatedSession,
    authorization: Authorization = None,
) -> tuple[CurrentUser, AsyncSession] | None:
    if not uses_auth_db():
        await run_in_threadpool(_check_mock_access, authorization)
        return None
    if user is None or auth is None:
        raise unauthorized()

    db = auth[1]
    if request.method != "GET":
        # Keep account mutations serialized through commit, including A80's service transaction.
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                         {"key": f"me:{user.claims.user_id}"})
        if not await run_in_threadpool(account_is_active, user.claims.user_id):
            raise unauthorized()
    return user, db


MeSession = Annotated[tuple[CurrentUser, AsyncSession] | None, Depends(_get_me_session)]
