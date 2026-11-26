from typing import Annotated

from fastapi import APIRouter, Depends, Path
from ulid import ULID

from api.auth.tokens import uses_auth_db
from api.deps import CurrentUser, require_role
from api.mocks import notices as mock_notices
from api.repositories.notices import postgres_store
from api.schemas.notices import (
    NOTICE_ID_PATTERN, NoticeCreate, NoticeDecisionResult, NoticeEnd, NoticeResult, NoticeReview, NoticeUpdate,
)
from api.services.notices import NoticeStore

router = APIRouter(prefix="/admin/notices")
Operator = Annotated[CurrentUser, Depends(require_role("operator", "admin"))]
NoticeId = Annotated[str, Path(pattern=NOTICE_ID_PATTERN)]


def _store() -> NoticeStore:
    return postgres_store if uses_auth_db() else mock_notices.memory_store


@router.post("", status_code=201)
def create_notice(payload: NoticeCreate, operator: Operator) -> NoticeResult:
    record = _store().create("ntc_" + str(ULID()), payload, operator.claims.user_id)
    return NoticeResult(notice_id=record.notice_id, approval_status=record.approval_status)


@router.patch("/{notice_id}")
def update_notice(notice_id: NoticeId, payload: NoticeUpdate, operator: Operator) -> NoticeResult:
    record = _store().change(notice_id, "update", operator.claims.user_id, patch=payload)
    return NoticeResult(notice_id=record.notice_id, approval_status=record.approval_status)


@router.post("/{notice_id}/review")
def review_notice(notice_id: NoticeId, payload: NoticeReview, operator: Operator) -> NoticeDecisionResult:
    record = _store().change(notice_id, payload.decision, operator.claims.user_id, reason=payload.reason)
    return NoticeDecisionResult(
        notice_id=record.notice_id, approval_status=record.approval_status, control_version=record.control_version,
    )


@router.post("/{notice_id}/end")
def end_notice(notice_id: NoticeId, operator: Operator, payload: NoticeEnd | None = None) -> NoticeDecisionResult:
    record = _store().change(notice_id, "end", operator.claims.user_id, reason=payload.reason if payload else None)
    return NoticeDecisionResult(
        notice_id=record.notice_id, approval_status=record.approval_status, control_version=record.control_version,
    )
