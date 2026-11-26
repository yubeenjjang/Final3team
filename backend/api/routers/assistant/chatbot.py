from dataclasses import replace
from secrets import token_urlsafe
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Request, Response
from starlette.concurrency import run_in_threadpool

from api.auth.tokens import unauthorized, uses_auth_db
from api.deps import Authorization, CurrentUser, get_current_user
from api.jobs.assistant_queue import AssistantQueue, PostgresAssistantQueue
from api.mocks.store import auth_lock
from api.schemas.assistant import RUN_ID_PATTERN, AssistantRequest
from api.services import assistant, mock_assistant
from api.services.mock_auth import authenticated_access

router = APIRouter()
queue: AssistantQueue = PostgresAssistantQueue()
RunId = Annotated[str, Path(pattern=RUN_ID_PATTERN)]
RunToken = Annotated[str | None, Header(alias="X-Run-Access-Token")]
RouteToken = Annotated[str | None, Header(alias="X-Route-Access-Token")]


async def run_access(
    request: Request,
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    authorization: Authorization = None,
    token: RunToken = None,
    route_token: RouteToken = None,
) -> assistant.RunAccess:
    user_id = user.claims.user_id if user else None
    if authorization is not None and not uses_auth_db():
        if assistant.uses_assistant_db():
            raise unauthorized()

        def mock_user_id() -> UUID:
            with auth_lock:
                return UUID(authenticated_access(authorization, assistant.now())[1].user_id)

        user_id = await run_in_threadpool(mock_user_id)
    return assistant.RunAccess(
        user_id, token, assistant.anonymous_session(request.cookies.get(assistant.ANONYMOUS_COOKIE)), route_token,
    )


Access = Annotated[assistant.RunAccess, Depends(run_access)]


@router.post("/assistant/query", status_code=202)
async def submit_run(
    request: Request, response: Response, run: AssistantRequest, access: Access,
) -> dict[str, object]:
    session_created = access.user_id is None and access.session is None
    if session_created:
        access = replace(access, session=token_urlsafe(32))
    assistant.enforce_rate_limit(request.client.host if request.client else "unknown", access.user_id)
    body = await request.json()
    submit = queue.enqueue if assistant.uses_assistant_db() else mock_assistant.create_run
    result = await run_in_threadpool(submit, run, body, access)
    if session_created:
        response.set_cookie(
            assistant.ANONYMOUS_COOKIE, access.session, httponly=True, secure=request.url.scheme == "https",
            samesite="lax", max_age=int(assistant.TOKEN_TTL.total_seconds()), path="/api/v1/assistant",
        )
    return result
