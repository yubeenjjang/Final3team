from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.auth.tokens import uses_auth_db
from api.deps import CurrentUser, require_role
from api.repositories.reports import PostgresReports
from api.schemas import reports as schema
from api.schemas.chat import MAX_BIGINT
from api.services import mock_reports, reports as rules

router = APIRouter(prefix="/admin/reports")
Reviewer = Annotated[CurrentUser, Depends(require_role("operator", "admin"))]
_db_store = PostgresReports()


def _store() -> rules.ReportReviewStore:
    return _db_store if uses_auth_db() else mock_reports.mock_reports


@router.get("")
def read_reports(
    reviewer: Reviewer,
    status: schema.ReportStatus | None = None,
    page: Annotated[int, Query(ge=1, le=MAX_BIGINT // rules.PAGE_SIZE)] = 1,
    report_id: Annotated[str | None, Query(pattern=schema.REPORT_ID_PATTERN)] = None,
) -> schema.ReportPage | schema.ReportDetail:
    store = _store()
    if report_id is not None:
        return store.detail(reviewer.claims.user_id, report_id)
    return store.list(status, page)


@router.post("")
def decide_report(request: schema.ReportDecision, reviewer: Reviewer) -> schema.ReportResult:
    return _store().decide(reviewer.claims.user_id, request)
