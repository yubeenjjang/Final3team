from typing import Annotated

from fastapi import APIRouter, Header, Response

from api.schemas.auth import LoginRequest, RefreshRequest, SignupRequest
from api.services import mock_auth

router = APIRouter(prefix="/auth")
Authorization = Annotated[str | None, Header()]


@router.post("/signup", status_code=201)
def signup(request: SignupRequest) -> dict[str, object]:
    return mock_auth.signup(request)


@router.post("/login")
def login(request: LoginRequest) -> dict[str, object]:
    return mock_auth.login(request)


@router.post("/refresh")
def refresh(request: RefreshRequest) -> dict[str, object]:
    return mock_auth.refresh(request.refresh_token.get_secret_value())


@router.post("/logout", status_code=204)
def logout(request: RefreshRequest, authorization: Authorization = None) -> Response:
    mock_auth.logout(authorization, request.refresh_token.get_secret_value())
    return Response(status_code=204)
