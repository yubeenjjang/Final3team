from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import (
    AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, model_validator,
)

from api.schemas.festivals import CopyrightType, FestivalStatus, RegionCode, _parse_query_date


def _check_text(value: str) -> str:
    if "\x00" in value:
        raise ValueError("문자열에 잘못된 문자가 있습니다.")
    return value


def _check_address(value: str) -> str:
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError("주소는 한 줄로 입력해 주세요.")
    return value


def _check_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or any(char.isspace() for char in value):
        raise ValueError("HTTP 또는 HTTPS URL을 입력해 주세요.")
    return value


def _check_date(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    return _parse_query_date(value)


def _check_coordinate(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("좌표는 숫자로 입력해 주세요.")
    return value


Text = Annotated[str, Field(min_length=1), AfterValidator(_check_text)]
Address = Annotated[Text, AfterValidator(_check_address)]
WebUrl = Annotated[Text, AfterValidator(_check_url)]
FestivalDate = Annotated[date, BeforeValidator(_check_date)]
Latitude = Annotated[Decimal, BeforeValidator(_check_coordinate), Field(ge=33, le=39, decimal_places=6)]
Longitude = Annotated[Decimal, BeforeValidator(_check_coordinate), Field(ge=124, le=132, decimal_places=6)]


class AdminImageCopyright(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: CopyrightType
    credit: Text | None = None
    modify_allowed: StrictBool | None = None

    @model_validator(mode="after")
    def validate_modify_allowed(self) -> "AdminImageCopyright":
        if self.modify_allowed is not None and self.modify_allowed != (self.type == "Type1"):
            raise ValueError("이미지 변경 허용 여부는 저작권 유형과 일치해야 합니다.")
        return self


class FestivalFields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)

    name: Text | None = None
    region_code: RegionCode | None = None
    start_date: FestivalDate | None = None
    end_date: FestivalDate | None = None
    venue_name: Text | None = None
    lat: Latitude | None = None
    lng: Longitude | None = None
    address: Address | None = None
    overview: Text | None = None
    fee_text: Text | None = None
    homepage_url: WebUrl | None = None
    event_status: FestivalStatus | None = None
    image_url: WebUrl | None = None
    thumbnail_url: WebUrl | None = None
    image_copyright: AdminImageCopyright | None = None
    reason: Text

    @model_validator(mode="after")
    def validate_non_nullable_fields(self) -> "FestivalFields":
        for field in ("name", "region_code", "start_date", "end_date", "venue_name", "lat", "lng", "event_status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field}에 값을 입력해 주세요.")
        return self


class FestivalRegistration(FestivalFields):
    name: Text
    region_code: RegionCode
    start_date: FestivalDate
    end_date: FestivalDate
    venue_name: Text
    lat: Latitude
    lng: Longitude


class FestivalUpdate(FestivalFields):
    published: StrictBool | None = None

    @model_validator(mode="after")
    def validate_update(self) -> "FestivalUpdate":
        if self.model_fields_set == {"reason"} or ("published" in self.model_fields_set and self.published is None):
            raise ValueError("수정할 필드 또는 게시 여부를 입력해 주세요.")
        return self


class FestivalRegistrationResult(BaseModel):
    festival_id: str
    review_status: Literal["pending"] = "pending"


class FestivalUpdateResult(BaseModel):
    festival_id: str
    review_status: Literal["pending", "approved", "hidden"]
    published_at: datetime | None
