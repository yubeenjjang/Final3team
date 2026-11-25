from collections.abc import Mapping
from datetime import datetime
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from api.errors import ApiError
from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY, FESTIVAL_CLASS
from api.schemas.festival_review import (
    ApprovalStatus, FestivalPatch, ReviewPage, ReviewReason, ReviewRequest, ReviewResult,
)


class ReviewStore(Protocol):
    def list_items(
        self, status: ApprovalStatus, reason: ReviewReason | None, page: int, page_size: int,
    ) -> ReviewPage: ...

    def decide(self, request: ReviewRequest, reviewer: UUID) -> ReviewResult: ...


def review_changes(
    request: ReviewRequest, festival: Mapping[str, object], proposal: object, now: datetime,
) -> dict[str, object]:
    if request.decision == "reject":
        return {}
    if request.decision == "hide":
        return {"review_status": "hidden", "published_at": None}

    # 이전 증빙 수집기는 변경 값을 문자열로 저장했습니다.
    if request.value is None and isinstance(proposal, dict):
        proposal = {key: None if value == "None" else value for key, value in proposal.items()}
    try:
        patch = FestivalPatch.model_validate(request.value if request.value is not None else (
            {} if proposal is None else proposal
        )).model_dump(exclude_unset=True)
    except ValidationError:
        raise ApiError(422, "VALIDATION_ERROR", "적용할 축제 필드와 값을 확인해 주세요.") from None

    effective = {**festival, **patch}
    if effective["category"] != FESTIVAL_CATEGORY or effective["source_class_level2"] != FESTIVAL_CLASS:
        raise ApiError(422, "VALIDATION_ERROR", "EV01로 확인된 축제만 승인할 수 있습니다.")

    lat, lng = effective["latitude"], effective["longitude"]
    no_coords = lat is None and lng is None
    if no_coords:
        valid_location = not (effective["address"] or "").strip() and effective["coords_source"] is None
    else:
        valid_location = lat is not None and lng is not None and 33 <= lat <= 39 and 124 <= lng <= 132
    if not valid_location:
        raise ApiError(422, "VALIDATION_ERROR", "주소와 대한민국 범위의 위도·경도 두 값을 확인해 주세요.")

    start, end = effective["start_date"], effective["end_date"]
    if start is not None and end is not None and start > end:
        raise ApiError(422, "VALIDATION_ERROR", "축제 기간을 확인해 주세요.")
    if not all(effective[key] for key in ("title", "region_code", "event_status")) or (
        effective["image_url"] is not None and effective["image_copyright_type"] is None
    ):
        raise ApiError(422, "VALIDATION_ERROR", "필수 축제 정보와 이미지 저작권을 확인해 주세요.")
    published_at = festival["published_at"] if festival["review_status"] == "approved" else None
    return {**patch, "review_status": "approved", "published_at": published_at or now}


def check_pending(status: ApprovalStatus | None) -> None:
    if status is None:
        raise ApiError(404, "QUEUE_ITEM_NOT_FOUND", "검토 항목을 찾을 수 없습니다.")
    if status != "pending":
        raise ApiError(409, "ALREADY_REVIEWED", "이미 처리된 검토 항목입니다.")
