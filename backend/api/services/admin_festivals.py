from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from api.errors import ApiError
from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY, FESTIVAL_CLASS, KST, _event_status
from api.schemas.admin_festivals import (
    FestivalFields, FestivalRegistration, FestivalRegistrationResult, FestivalUpdate, FestivalUpdateResult,
)

ADMIN_SOURCE_ID = "admin_manual"
ADMIN_IMAGE_CREDIT = "관리자 등록"
IDENTITY_FIELDS = ("title", "start_date", "end_date", "venue_name")
_COLUMN_NAMES = {
    "name": "title", "lat": "latitude", "lng": "longitude", "overview": "summary",
    "fee_text": "admission_fee_text", "homepage_url": "official_url",
    "image_copyright": "image_copyright_type",
}


class AdminFestivalStore(Protocol):
    def register(self, request: FestivalRegistration, actor: UUID) -> FestivalRegistrationResult: ...

    def update(self, festival_id: str, request: FestivalUpdate, actor: UUID) -> FestivalUpdateResult: ...


def _fields(request: FestivalFields) -> dict[str, object]:
    raw = request.model_dump(exclude_unset=True, exclude={"reason", "published"})
    if raw.get("image_copyright") is not None:
        raw["image_copyright"] = request.image_copyright.type
    return {_COLUMN_NAMES.get(field, field): value for field, value in raw.items()}


def _validate_festival(festival: Mapping[str, object]) -> None:
    if festival["category"] != FESTIVAL_CATEGORY or festival["source_class_level2"] != FESTIVAL_CLASS:
        raise ApiError(422, "VALIDATION_ERROR", "EV01 축제만 관리할 수 있습니다.")
    start, end = festival["start_date"], festival["end_date"]
    if start is not None and end is not None and start > end:
        raise ApiError(422, "VALIDATION_ERROR", "시작일은 종료일 이하여야 합니다.")
    lat, lng = festival["latitude"], festival["longitude"]
    if lat is None and lng is None:
        valid_location = not (festival.get("address") or "").strip() and festival.get("coords_source") is None
    else:
        valid_location = lat is not None and lng is not None and 33 <= lat <= 39 and 124 <= lng <= 132
    if not valid_location:
        raise ApiError(422, "VALIDATION_ERROR", "주소와 대한민국 범위의 위도·경도 두 값을 확인해 주세요.")
    if festival.get("image_url") is not None and festival.get("image_copyright_type") is None:
        raise ApiError(422, "VALIDATION_ERROR", "대표 이미지의 저작권 유형을 입력해 주세요.")


def registration_fields(request: FestivalRegistration) -> dict[str, object]:
    values = _fields(request)
    values.setdefault("event_status", _event_status(request.start_date, request.end_date, datetime.now(KST).date()))
    values.update(category=FESTIVAL_CATEGORY, source_class_level2=FESTIVAL_CLASS)
    _validate_festival(values)
    return values


def update_fields(
    request: FestivalUpdate, festival: Mapping[str, object], now: datetime,
) -> dict[str, object]:
    updates = _fields(request)
    if any(key in updates and updates[key] != festival[key] for key in ("latitude", "longitude")):
        updates["coords_source"] = None
    _validate_festival({**festival, **updates})
    if request.published is True:
        updates.update(review_status="approved", published_at=festival["published_at"] or now)
    elif request.published is False:
        updates.update(review_status="hidden")
    return {field: value for field, value in updates.items() if festival.get(field) != value}


def update_result(festival_id: str, festival: Mapping[str, object]) -> FestivalUpdateResult:
    status = festival["review_status"]
    return FestivalUpdateResult(
        festival_id=festival_id, review_status=status,
        published_at=festival["published_at"] if status == "approved" else None,
    )


def audit_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def duplicate_proposal(fields: Mapping[str, object]) -> dict[str, object]:
    return {**{field: audit_value(value) for field, value in fields.items()}, "coords_source": None}


def duplicate_error() -> ApiError:
    return ApiError(409, "DUPLICATE_FESTIVAL", "같은 이름·기간·장소의 축제가 있어 검토 대기열로 보냈습니다.")


def missing_festival() -> ApiError:
    return ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
