from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints

ReviewReason = Literal[
    "duplicate", "conflict", "missing_location", "date_unclear",
    "not_festival_class", "class_unverified", "missing_from_source", "coords_out_of_range",
]
ApprovalStatus = Literal["pending", "approved", "rejected"]
Decision = Literal["approve", "reject", "hide"]
NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ReviewNote = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class FestivalPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    title: NonEmpty | None = None
    region_code: NonEmpty | None = None
    category: str | None = None
    source_class_level1: str | None = None
    source_class_level2: str | None = None
    source_class_code: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    venue_name: str | None = None
    address: str | None = None
    latitude: Annotated[Decimal, Field(ge=33, le=39, decimal_places=6)] | None = None
    longitude: Annotated[Decimal, Field(ge=124, le=132, decimal_places=6)] | None = None
    coords_source: Literal["tourapi", "geocoded"] | None = None
    summary: str | None = None
    description: str | None = None
    admission_fee_text: str | None = None
    image_url: str | None = None
    thumbnail_url: str | None = None
    image_copyright_type: Literal["Type1", "Type3"] | None = None
    official_url: str | None = None
    organizer: str | None = None
    event_status: Literal["upcoming", "ongoing", "ended", "cancelled", "needs_review"] | None = None


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue_id: Annotated[int, Field(strict=True, ge=1, le=2**63 - 1)]
    decision: Decision
    value: dict[str, object] | None = None
    note: ReviewNote = Field(validation_alias=AliasChoices("note", "reason"))


class ReviewItem(BaseModel):
    queue_id: int
    festival_id: str
    festival_name: str
    reason: ReviewReason
    proposed_value: dict[str, object] | None
    approval_status: ApprovalStatus
    created_at: datetime


class ReviewPage(BaseModel):
    items: list[ReviewItem]
    total: int
    page: int
    page_size: int


class ReviewResult(BaseModel):
    queue_id: int
    approval_status: Literal["approved", "rejected"]
    applied: bool
