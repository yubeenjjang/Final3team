"""공지 상태 전이와 A07·길찾기가 공유하는 통제 규칙."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from pydantic import ValidationError

from api.errors import ApiError
from api.providers.route_base import KST
from api.schemas.festival_info import Notice, NoticeType
from api.schemas.notices import ApprovalStatus, NoticeCreate, NoticeUpdate

Action = Literal["create", "update", "approve", "reject", "end"]
SOURCE_ID = "admin_manual"
NO_CONTROL_VERSION = "none"
CONTROL_CHANGED_CODE = "ROUTE_CONTROL_CHANGED"
CONTROL_CHANGED_MESSAGE = "공식 교통통제가 바뀌었어요. 경로를 다시 조회해 주세요."
_CONTROL_TITLES_LIMIT = 3


@dataclass(frozen=True)
class NoticeRecord:
    notice_id: str
    festival_id: str | None
    type: NoticeType
    title: str
    content: str | None
    effective_from: datetime | None
    effective_to: datetime | None
    source_url: str | None
    approval_status: ApprovalStatus = "pending"
    published_at: datetime | None = None
    ended_at: datetime | None = None
    control_version: str | None = None

    @property
    def effective_end(self) -> datetime | None:
        return min(
            (time for time in (self.effective_to, self.ended_at) if time is not None), default=None,
        )

    def public(self) -> Notice:
        return Notice(
            notice_id=self.notice_id, type=self.type, title=self.title, content=self.content,
            effective_from=self.effective_from, effective_to=self.effective_end,
            source=SOURCE_ID, source_url=self.source_url, published_at=self.published_at,
            control_version=self.control_version,
        )


@dataclass(frozen=True)
class ControlSnapshot:
    version: str = NO_CONTROL_VERSION
    titles: tuple[str, ...] = ()

    def apply_to(self, notices: list[str], festival_id: str) -> list[str]:
        if not self.titles:
            return notices
        titles = ", ".join(self.titles[:_CONTROL_TITLES_LIMIT])
        detail = f"/api/v1/festivals/{festival_id}/notices"
        return [f"공식 교통통제 공지 ({detail}) {titles}", *notices]


class ControlReader(Protocol):
    def snapshot(self, festival_id: str, now: datetime | None = None) -> ControlSnapshot: ...


class NoticeStore(ControlReader, Protocol):
    def create(self, notice_id: str, payload: NoticeCreate, actor: UUID) -> NoticeRecord: ...

    def change(
        self, notice_id: str, action: Action, actor: UUID,
        *, patch: NoticeUpdate | None = None, reason: str | None = None,
    ) -> NoticeRecord: ...


def now_kst() -> datetime:
    return datetime.now(KST)


def control_version(revision: int) -> str:
    return f"cv{revision}" if revision else NO_CONTROL_VERSION


def new_record(notice_id: str, payload: NoticeCreate) -> NoticeRecord:
    return NoticeRecord(
        notice_id=notice_id,
        **payload.model_dump(exclude={"source_url"}),
        source_url=str(payload.source_url),
    )


def apply_change(
    before: NoticeRecord, action: Action, now: datetime, patch: NoticeUpdate | None,
) -> NoticeRecord:
    if action == "update":
        assert patch is not None
        changes = patch.model_dump(exclude_unset=True)
        if "source_url" in changes:
            changes["source_url"] = str(changes["source_url"])
        after = replace(
            before, **changes, approval_status="pending", published_at=None,
            ended_at=None, control_version=None,
        )
        if after.effective_from is not None and after.effective_to is not None:
            if after.effective_from >= after.effective_to:
                raise ApiError(422, "VALIDATION_ERROR", "효력 종료는 시작 이후여야 합니다.")
        return after

    if action == "end":
        if before.approval_status != "approved":
            raise ApiError(409, "NOTICE_NOT_APPROVED", "승인된 공지만 종료할 수 있어요.")
        if before.effective_end is not None and before.effective_end <= now:
            raise ApiError(409, "ALREADY_ENDED", "이미 종료된 공지예요.")
        return replace(before, ended_at=now)

    if before.approval_status != "pending":
        raise ApiError(409, "ALREADY_REVIEWED", "이미 검토한 공지예요.")
    if action == "reject":
        return replace(before, approval_status="rejected", control_version=None)

    assert action == "approve"
    try:
        NoticeCreate.model_validate({
            name: getattr(before, name) for name in NoticeCreate.model_fields
        })
    except ValidationError:
        raise ApiError(422, "VALIDATION_ERROR", "공지 본문, 출처 URL과 효력 기간을 확인해 주세요.") from None
    return replace(before, approval_status="approved", published_at=now)


def active_at(start: datetime | None, end: datetime | None, now: datetime) -> bool:
    return (start is None or start <= now) and (end is None or now < end)


def notice_not_found() -> ApiError:
    return ApiError(404, "NOTICE_NOT_FOUND", "공지를 찾을 수 없어요.")


def festival_not_found() -> ApiError:
    return ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없어요.")
