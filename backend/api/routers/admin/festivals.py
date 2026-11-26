from typing import Annotated

from fastapi import APIRouter, Depends, Path

from api.auth.tokens import uses_auth_db
from api.deps import CurrentUser, require_role
from api.mocks.admin_festivals import mock_festival_store
from api.repositories.admin_festivals import PostgresAdminFestivalStore
from api.schemas.admin_festivals import (
    FestivalRegistration, FestivalRegistrationResult, FestivalUpdate, FestivalUpdateResult,
)
from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.services.admin_festivals import AdminFestivalStore

router = APIRouter(prefix="/admin/festivals")
Admin = Annotated[CurrentUser, Depends(require_role("admin"))]
_db_store = PostgresAdminFestivalStore()


def _store() -> AdminFestivalStore:
    return _db_store if uses_auth_db() else mock_festival_store


@router.post("", status_code=201)
def register_festival(request: FestivalRegistration, admin: Admin) -> FestivalRegistrationResult:
    return _store().register(request, admin.claims.user_id)


@router.patch("/{festival_id}")
def update_festival(
    festival_id: Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)], request: FestivalUpdate, admin: Admin,
) -> FestivalUpdateResult:
    return _store().update(festival_id, request, admin.claims.user_id)
