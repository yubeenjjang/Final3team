import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

# 공개 상태와 수집 메타데이터는 018의 분류·보류 판단을 따릅니다.
EDITABLE_FIELDS = {
    "title", "region_code", "start_date", "end_date", "venue_name", "address",
    "latitude", "longitude", "coords_source", "summary", "description", "admission_fee_text",
    "official_url", "event_status", "image_url", "thumbnail_url", "image_copyright_type",
}
LOCATION_FIELDS = {"address", "latitude", "longitude", "coords_source"}
DATE_FIELDS = {"start_date", "end_date"}
IMAGE_FIELDS = {"image_url", "thumbnail_url", "image_copyright_type"}


def conflicting_fields(
    previous: Mapping[str, object], changes: Mapping[str, object], edited: set[str],
) -> set[str]:
    conflicts = edited.intersection(changes)
    if edited & LOCATION_FIELDS:
        # 주소·좌표·출처는 같은 장소를 가리키는 한 묶음입니다.
        conflicts.update(LOCATION_FIELDS.intersection(changes))
    if edited & IMAGE_FIELDS:
        # 공급원 이미지는 동일한 저작권 유형과 한 묶음으로 이동합니다.
        conflicts.update(IMAGE_FIELDS.intersection(changes))
    if conflicts & DATE_FIELDS:
        start, end = (
            previous[field] if field in conflicts else changes.get(field, previous[field])
            for field in ("start_date", "end_date")
        )
        if start is not None and end is not None and start > end:
            conflicts.update(DATE_FIELDS.intersection(changes))
    return conflicts


def _json_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"지원하지 않는 변경 값 형식: {type(value).__name__}")


def protect_admin_edits(
    db: Connection | Session, festival_id: str, previous: Mapping[str, object], changes: dict[str, object],
    *, queue_conflicts: bool = True,
) -> set[str]:
    """축제 행을 잠근 호출자가 공급원 변경 중 보류할 칸을 검토 대기열로 옮깁니다."""
    if not EDITABLE_FIELDS.intersection(changes):
        return set()
    edited = set(db.scalars(text("""
        SELECT DISTINCT field FROM public.festival_change_history
        WHERE festival_id = :id AND actor = 'admin'
    """), {"id": festival_id})) & EDITABLE_FIELDS
    conflicts = conflicting_fields(previous, changes, edited)
    if not conflicts:
        return conflicts

    blocked = {field: changes.pop(field) for field in conflicts}
    if not queue_conflicts:
        return conflicts
    proposal = json.dumps(blocked, default=_json_value)
    params = {"id": festival_id, "proposal": proposal}
    pending = db.scalar(text("""
        SELECT queue_id FROM public.festival_review_queue
        WHERE festival_id = :id AND reason = 'conflict' AND approval_status = 'pending'
        ORDER BY queue_id LIMIT 1
    """), params)
    if pending is None:
        db.execute(text("""
            INSERT INTO public.festival_review_queue (festival_id, reason, proposed_value)
            VALUES (:id, 'conflict', CAST(:proposal AS jsonb))
        """), params)
    else:
        db.execute(text("""
            UPDATE public.festival_review_queue
            SET proposed_value = CASE WHEN jsonb_typeof(proposed_value) = 'object'
                THEN proposed_value || CAST(:proposal AS jsonb) ELSE CAST(:proposal AS jsonb) END
            WHERE queue_id = :queue_id
        """), {**params, "queue_id": pending})
    return conflicts
