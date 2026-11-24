from typing import Annotated

from fastapi import APIRouter, Query, Response
from starlette.concurrency import run_in_threadpool

from api.deps import Authorization
from api.repositories import users as repository
from api.routers.accounts.dependencies import MeSession
from api.schemas.users import (
    AccountDeletion,
    ActivityType,
    CompanionActivity,
    FestivalPreferences,
    PreferencesUpdate,
    Profile,
    ProfileUpdate,
)
from api.services import account_deletion, mock_users

router = APIRouter(prefix="/me")


@router.get("/festival-preferences")
async def get_preferences(auth: MeSession, authorization: Authorization = None) -> FestivalPreferences:
    if auth is None:
        return await run_in_threadpool(mock_users.get_preferences, authorization)
    return await repository.get_preferences(auth[1])


@router.put("/festival-preferences")
async def save_preferences(
    request: PreferencesUpdate, auth: MeSession, authorization: Authorization = None,
) -> FestivalPreferences:
    if auth is None:
        return await run_in_threadpool(mock_users.save_preferences, authorization, request)
    return await repository.save_preferences(auth[1], request)


@router.get("/profile")
async def get_profile(auth: MeSession, authorization: Authorization = None) -> Profile:
    if auth is None:
        return await run_in_threadpool(mock_users.get_profile, authorization)
    return await repository.get_profile(auth[1])


@router.patch("/profile")
async def update_profile(request: ProfileUpdate, auth: MeSession, authorization: Authorization = None) -> Profile:
    if auth is None:
        return await run_in_threadpool(mock_users.get_profile, authorization, request)
    return await repository.update_profile(auth[1], request)


@router.get("/companion-activity")
async def get_companion_activity(
    activity: Annotated[ActivityType, Query(alias="type")], auth: MeSession, authorization: Authorization = None,
) -> CompanionActivity:
    if auth is None:
        return await run_in_threadpool(mock_users.get_companion_activity, authorization)
    return await repository.get_companion_activity(auth[1], activity)


@router.delete("", status_code=204)
async def delete_account(request: AccountDeletion, auth: MeSession, authorization: Authorization = None) -> Response:
    password = request.password.get_secret_value()
    if auth is None:
        await run_in_threadpool(mock_users.delete_account, authorization, password)
    else:
        await run_in_threadpool(account_deletion.delete_account, auth[0].claims, password)
    return Response(status_code=204)
