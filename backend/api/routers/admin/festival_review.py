from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.auth.tokens import uses_auth_db
from api.deps import CurrentUser, require_role
from api.mocks.festival_review import MemoryReviewStore
from api.repositories.festival_review import PostgresReviewStore
from api.schemas.festival_review import ApprovalStatus, ReviewPage, ReviewReason, ReviewRequest, ReviewResult
from api.services.festival_review import ReviewStore

router = APIRouter(prefix="/admin/festivals/review-queue")
Reviewer = Annotated[CurrentUser, Depends(require_role("operator", "admin"))]
_mock_store = MemoryReviewStore()
_db_store = PostgresReviewStore()


def _store() -> ReviewStore:
    return _db_store if uses_auth_db() else _mock_store


@router.get("")
def get_review_queue(
    reviewer: Reviewer,
    approval_status: ApprovalStatus = "pending",
    reason: ReviewReason | None = None,
    page: Annotated[int, Query(ge=1, le=2**31 - 1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ReviewPage:
    return _store().list_items(approval_status, reason, page, page_size)


@router.post("")
def decide_review(request: ReviewRequest, reviewer: Reviewer) -> ReviewResult:
    return _store().decide(request, reviewer.claims.user_id)
