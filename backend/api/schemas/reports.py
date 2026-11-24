from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from api.schemas.chat import valid_text

REPORT_ID_PATTERN = r"^rpt_[0-9A-Za-z]{6,26}$"
ReportId = Annotated[str, Field(pattern=REPORT_ID_PATTERN)]
TargetType = Literal["companion_post", "chat_message", "chat_room", "user"]
ReportReason = Literal["spam", "abuse", "harassment", "fraud", "privacy", "other"]
ReportStatus = Literal["received", "reviewing", "actioned", "dismissed"]
ReportAction = Literal["dismiss", "hide_message", "hide_post", "close_room", "block_user"]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_type: TargetType
    target_id: str
    reason: ReportReason
    detail: Annotated[str, Field(max_length=500), AfterValidator(valid_text)] | None = None


class ReportCreated(BaseModel):
    report_id: ReportId


class ReportDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: ReportId
    action: ReportAction
    note: Annotated[str, AfterValidator(valid_text)]


class ReportSummary(ReportCreated):
    target_type: TargetType
    target_id: str
    reason: ReportReason
    status: ReportStatus
    created_at: datetime


class ReportPage(BaseModel):
    items: list[ReportSummary]
    page: int


class ReportRoom(BaseModel):
    room_id: str
    room_type: Literal["companion", "direct", "friend_group"]
    name: str | None
    status: Literal["active", "read_only", "closed"]


class ReportMessage(BaseModel):
    message_id: int
    seq: int
    sender_id: UUID | None
    body: str | None
    created_at: datetime


class ReportDetail(BaseModel):
    report: ReportSummary
    room: ReportRoom | None
    message: ReportMessage | None
    access_id: int | None


class ReportResult(ReportCreated):
    status: Literal["actioned", "dismissed"]
    handled_by: UUID
    handled_at: datetime
