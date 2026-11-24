from datetime import datetime, timezone
from threading import Lock
from uuid import UUID

from api.schemas.festival_review import (
    ApprovalStatus, FestivalPatch, ReviewItem, ReviewPage, ReviewReason, ReviewRequest, ReviewResult,
)
from api.services.festival_review import check_pending, review_changes


class MemoryReviewStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[int, ReviewItem] = {}
        self._festivals: dict[str, dict[str, object]] = {}
        for queue_id, reason in enumerate((
            "duplicate", "conflict", "not_festival_class", "class_unverified",
            "missing_from_source", "coords_out_of_range",
        ), start=1):
            festival_id = f"fst_REVIEW{queue_id}"
            title = f"검토 예시 축제 {queue_id}"
            self._items[queue_id] = ReviewItem(
                queue_id=queue_id, festival_id=festival_id, festival_name=title, reason=reason,
                proposed_value=None, approval_status="pending",
                created_at=datetime(2026, 11, 24, tzinfo=timezone.utc),
            )
            self._festivals[festival_id] = {
                **FestivalPatch().model_dump(),
                "title": title, "region_code": "SEOUL", "category": "festival",
                "source_class_level2": {"not_festival_class": "EV02", "class_unverified": None}.get(reason, "EV01"),
                "address": "서울특별시" if reason == "coords_out_of_range" else None,
                "event_status": "upcoming", "review_status": "pending", "published_at": None,
            }

    def list_items(
        self, status: ApprovalStatus, reason: ReviewReason | None, page: int, page_size: int,
    ) -> ReviewPage:
        with self._lock:
            items = [
                item for item in reversed(self._items.values())
                if item.approval_status == status and (reason is None or item.reason == reason)
            ]
            offset = (page - 1) * page_size
            return ReviewPage(items=items[offset:offset + page_size], total=len(items), page=page, page_size=page_size)

    def decide(self, request: ReviewRequest, reviewer: UUID) -> ReviewResult:
        with self._lock:
            item = self._items.get(request.queue_id)
            check_pending(item.approval_status if item else None)
            festival = self._festivals[item.festival_id]
            updates = review_changes(request, festival, item.proposed_value, datetime.now(timezone.utc))
            applied = any(festival[key] != value for key, value in updates.items())
            festival.update(updates)
            status = "approved" if request.decision == "approve" else "rejected"
            self._items[item.queue_id] = item.model_copy(update={
                "approval_status": status, "festival_name": festival["title"],
            })
            return ReviewResult(queue_id=item.queue_id, approval_status=status, applied=applied)
