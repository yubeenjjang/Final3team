import re
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from api.schemas.common import MockResponse

RegionCode = Literal[
    "SEOUL",
    "BUSAN",
    "DAEGU",
    "INCHEON",
    "GWANGJU",
    "DAEJEON",
    "ULSAN",
    "SEJONG",
    "GYEONGGI",
    "GANGWON",
    "CHUNGBUK",
    "CHUNGNAM",
    "JEONBUK",
    "JEONNAM",
    "GYEONGBUK",
    "GYEONGNAM",
    "JEJU",
]
FilterStatus = Literal["upcoming", "ongoing", "ended", "cancelled"]
FestivalStatus = FilterStatus | Literal["needs_review"]
CopyrightType = Literal["Type1", "Type3"]
FESTIVAL_ID_PATTERN = r"^fst_[0-9A-Za-z]{6,26}$"


def _parse_query_date(value: str) -> date:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    return date.fromisoformat(value)


QueryDate = Annotated[date, BeforeValidator(_parse_query_date)]


class FestivalQuery(BaseModel):
    region: RegionCode | Literal["ALL"] = "ALL"
    date_from: QueryDate | None = None
    date_to: QueryDate | None = None
    q: str | None = Field(default=None, min_length=1, max_length=50)
    status: FilterStatus | None = None
    sort: Literal["start_date", "-start_date", "name"] = "start_date"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ImageCopyright(BaseModel):
    type: CopyrightType
    credit: str
    modify_allowed: bool


class FestivalListItem(BaseModel):
    festival_id: str
    name: str
    region_code: RegionCode
    venue_name: str | None
    lat: float | None
    lng: float | None
    start_date: date | None
    end_date: date | None
    event_status: FestivalStatus
    thumbnail_url: str | None
    image_credit: str | None
    source: Literal["tourapi"] = "tourapi"
    last_synced_at: str


class FestivalDetail(FestivalListItem, MockResponse):
    address: str | None
    overview: str
    fee_text: str | None
    homepage_url: str | None
    image_url: str | None
    image_copyright: ImageCopyright | None
    source_ref: str


class FestivalPage(MockResponse):
    items: list[FestivalListItem]
    total: int
    page: int
    page_size: int
