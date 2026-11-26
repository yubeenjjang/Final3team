from typing import Annotated

from fastapi import APIRouter, Depends, Response
from starlette.concurrency import run_in_threadpool

from api.auth import service
from api.auth.tokens import unauthorized, uses_auth_db
from api.deps import Authorization, CurrentUser, get_current_user
from api.schemas.auth import LoginRequest, RefreshRequest, SignupRequest
from api.services import mock_auth

router = APIRouter(prefix="/auth")


@router.post("/signup", status_code=201)
def signup(request: SignupRequest) -> dict[str, object]:
    return service.signup(request) if uses_auth_db() else mock_auth.signup(request)


@router.post("/login")
def login(request: LoginRequest) -> dict[str, object]:
    return service.login(request) if uses_auth_db() else mock_auth.login(request)


@router.post("/refresh")
def refresh(request: RefreshRequest) -> dict[str, object]:
    token = request.refresh_token.get_secret_value()
    return service.refresh(token) if uses_auth_db() else mock_auth.refresh(token)


@router.post("/logout", status_code=204)
async def logout(
    request: RefreshRequest,
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    authorization: Authorization = None,
) -> Response:
    token = request.refresh_token.get_secret_value()
    if uses_auth_db():
        if user is None:
            raise unauthorized()
        await run_in_threadpool(service.logout, user.claims, token)
    else:
        await run_in_threadpool(mock_auth.logout, authorization, token)
    return Response(status_code=204)
