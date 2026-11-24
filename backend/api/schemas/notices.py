from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, AwareDatetime, BaseModel, BeforeValidator, ConfigDict, StringConstraints, model_validator

from api.schemas.festival_info import NoticeType
from api.schemas.festivals import FESTIVAL_ID_PATTERN

NOTICE_ID_PATTERN = r"^ntc_[0-9A-Za-z]{6,26}$"
FestivalId = Annotated[str, StringConstraints(pattern=FESTIVAL_ID_PATTERN)]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
ApprovalStatus = Literal["pending", "approved", "rejected"]


def _date_time(value: object) -> object:
    if not isinstance(value, (str, datetime)):
        raise ValueError("시간대가 포함된 date-time이 필요합니다.")
    # Pydantic도 숫자 문자열을 Unix 시각으로 해석하므로 ISO 날짜 구분자를 확인한다.
    if isinstance(value, str) and "T" not in value.upper():
        raise ValueError("시간대가 포함된 date-time이 필요합니다.")
    return value


EffectiveTime = Annotated[AwareDatetime, BeforeValidator(_date_time)]


class NoticeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: FestivalId | None = None
    type: NoticeType
    title: Title
    content: str
    effective_from: EffectiveTime
    effective_to: EffectiveTime
    source_url: AnyHttpUrl

    @model_validator(mode="after")
    def validate_period(self) -> "NoticeCreate":
        if self.effective_from >= self.effective_to:
            raise ValueError("효력 종료는 시작 이후여야 합니다.")
        return self


class NoticeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: FestivalId | None = None
    type: NoticeType | None = None
    title: Title | None = None
    content: str | None = None
    effective_from: EffectiveTime | None = None
    effective_to: EffectiveTime | None = None
    source_url: AnyHttpUrl | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "NoticeUpdate":
        fields = self.model_fields_set
        if not fields or any(getattr(self, name) is None for name in fields - {"festival_id"}):
            raise ValueError("수정할 값이 필요합니다.")
        return self


class NoticeEnd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: Reason | None = None


class NoticeReview(NoticeEnd):
    decision: Literal["approve", "reject"]

    @model_validator(mode="after")
    def validate_rejection(self) -> "NoticeReview":
        if self.decision == "reject" and self.reason is None:
            raise ValueError("반려 사유가 필요합니다.")
        return self


class NoticeResult(BaseModel):
    notice_id: str
    approval_status: ApprovalStatus


class NoticeDecisionResult(NoticeResult):
    control_version: str | None
