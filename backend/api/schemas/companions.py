from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

PostStatus = Literal["open", "full", "ended", "cancelled"]
ApplicationStatus = Literal["pending", "approved", "rejected", "cancelled"]
VisibleApplicationStatus = Literal["pending", "approved"]
ApplicationAction = Literal["approve", "reject", "cancel"]
PostAction = Literal["close", "end", "cancel"]
AgePreference = Literal["any", "20s", "30s", "40s", "50s_plus"]
GenderPreference = Literal["any", "female", "male"]
Capacity = Annotated[int, Field(strict=True, ge=1, le=10)]
Memo = Annotated[str, Field(max_length=500)]
FESTIVAL_ID_PATTERN = r"^fst_[0-9A-Za-z]{6,26}$"
POST_ID_PATTERN = r"^cpo_[0-9A-Za-z]{6,26}$"
APPLICATION_ID_PATTERN = r"^cap_[0-9A-Za-z]{6,26}$"


class CompanionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_null_byte(cls, value: object) -> object:
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("문자열에 NUL 문자를 사용할 수 없습니다.")
        return value


class PostCreate(CompanionInput):
    festival_id: Annotated[str, Field(pattern=FESTIVAL_ID_PATTERN)]
    meet_at: AwareDatetime
    capacity: Capacity
    age_pref: AgePreference | None = None
    gender_pref: GenderPreference = "any"
    memo: Memo | None = None


class PostUpdate(CompanionInput):
    meet_at: AwareDatetime | None = None
    capacity: Capacity | None = None
    age_pref: AgePreference | None = None
    gender_pref: GenderPreference | None = None
    memo: Memo | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("수정할 항목을 하나 이상 보내 주세요.")
        for field in self.model_fields_set & {"meet_at", "capacity", "gender_pref"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field}에 값이 필요합니다.")
        return self


class PostCreated(BaseModel):
    post_id: str
    room_id: str


class PostItem(BaseModel):
    post_id: str
    author_display_name: str | None
    meet_at: datetime
    capacity: int
    approved_count: int
    age_pref: AgePreference | None
    gender_pref: GenderPreference
    memo: str | None
    status: PostStatus


class PostDetail(PostItem):
    my_application_status: ApplicationStatus | None


class PostList(BaseModel):
    items: list[PostItem]


class FeedPostItem(PostItem):
    festival_id: str
    festival_name: str
    festival_thumbnail_url: str | None
    festival_venue_name: str | None
    festival_region_code: str


class FeedPostList(BaseModel):
    items: list[FeedPostItem]
    total: int
    page: int
    page_size: int


class PostChanged(BaseModel):
    post_id: str
    status: PostStatus


class ApplicationCreate(CompanionInput):
    message: Annotated[str, Field(max_length=200)] | None = None


class ApplicationCreated(BaseModel):
    application_id: str
    status: Literal["pending"] = "pending"


class ApplicationItem(BaseModel):
    application_id: str
    applicant_display_name: str | None
    applicant_age: int | None
    applicant_gender: Literal["male", "female"] | None
    message: str | None
    status: VisibleApplicationStatus
    created_at: datetime


class ApplicationList(BaseModel):
    items: list[ApplicationItem]


class ApplicationChanged(BaseModel):
    application_id: str
    status: Literal["approved", "rejected", "cancelled"]
    post_status: PostStatus


class MeetingPlace(CompanionInput):
    name: Annotated[str, Field(min_length=1, max_length=60)]
    address: str | None = None
    lat: Annotated[float, Field(ge=33, le=39)] | None = None
    lng: Annotated[float, Field(ge=124, le=132)] | None = None
    guide: Annotated[str, Field(max_length=300)] | None = None

    @model_validator(mode="after")
    def check_coordinate_pair(self) -> Self:
        if (self.lat is None) != (self.lng is None):
            raise ValueError("위도와 경도를 함께 보내 주세요.")
        return self


class MeetingPlaceDetail(MeetingPlace):
    updated_at: datetime


class MeetingPlaceUpdated(BaseModel):
    post_id: str
    updated_at: datetime


class MeetingPlaceUndecided(BaseModel):
    status: Literal["undecided"] = "undecided"
