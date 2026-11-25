from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from ulid import ULID

from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY, FESTIVAL_CLASS
from api.mocks.festival_review import MemoryReviewStore
from api.mocks.festivals import FESTIVALS, MockFestival
from api.schemas.admin_festivals import (
    FestivalRegistration, FestivalRegistrationResult, FestivalUpdate, FestivalUpdateResult,
)
from api.schemas.festival_review import FestivalPatch, ReviewItem
from api.services.admin_festivals import (
    ADMIN_IMAGE_CREDIT, IDENTITY_FIELDS, audit_value, duplicate_error, duplicate_proposal, missing_festival,
    registration_fields, update_fields, update_result,
)


class MemoryAdminFestivalStore(MemoryReviewStore):
    def __init__(self) -> None:
        super().__init__()
        self._empty_fields = FestivalPatch().model_dump()
        self.audit: list[dict[str, object]] = []
        self.catalog = {festival.festival_id: festival.model_copy(deep=True) for festival in FESTIVALS}
        for festival in FESTIVALS:
            self._festivals[festival.festival_id] = {
                **self._empty_fields, "title": festival.name, "region_code": festival.region_code,
                "category": festival.category,
                "source_class_level2": FESTIVAL_CLASS if festival.category == FESTIVAL_CATEGORY else None,
                "start_date": festival.start_date, "end_date": festival.end_date,
                "venue_name": festival.venue_name, "address": festival.address,
                "latitude": Decimal(str(festival.lat)) if festival.lat is not None else None,
                "longitude": Decimal(str(festival.lng)) if festival.lng is not None else None,
                "summary": festival.overview, "admission_fee_text": festival.fee_text,
                "official_url": festival.homepage_url, "event_status": festival.event_status,
                "image_url": festival.image_url, "thumbnail_url": festival.thumbnail_url,
                "image_copyright_type": festival.image_copyright.type if festival.image_copyright else None,
                "review_status": "approved", "published_at": datetime.fromisoformat(festival.last_synced_at),
                "source": festival.source, "source_ref": festival.source_ref,
                "last_synced_at": festival.last_synced_at,
            }

    def reset(self) -> None:
        fresh = MemoryAdminFestivalStore()
        with self._lock:
            self._items, self._festivals, self.audit = fresh._items, fresh._festivals, fresh.audit
            self.catalog.clear()
            self.catalog.update(fresh.catalog)

    def _write_history(
        self, festival_id: str, before: Mapping[str, object], changes: Mapping[str, object],
        reason: str, actor: UUID, now: datetime,
    ) -> None:
        self.audit.extend({
            "festival_id": festival_id, "field": field, "before_value": audit_value(before.get(field)),
            "after_value": audit_value(value), "actor": "admin", "actor_user_id": actor,
            "reason": reason, "changed_at": now,
        } for field, value in changes.items())

    def register(self, request: FestivalRegistration, actor: UUID) -> FestivalRegistrationResult:
        values = registration_fields(request)
        proposal = duplicate_proposal(values)
        with self._lock:
            now = datetime.now(timezone.utc)
            for festival_id, festival in self._festivals.items():
                if festival["category"] == FESTIVAL_CATEGORY and all(
                    festival[field] == values[field] for field in IDENTITY_FIELDS
                ):
                    if not any(
                        item.festival_id == festival_id and item.reason == "duplicate"
                        and item.approval_status == "pending" and item.proposed_value == proposal
                        for item in self._items.values()
                    ):
                        queue_id = max(self._items, default=0) + 1
                        self._items[queue_id] = ReviewItem(
                            queue_id=queue_id, festival_id=festival_id, festival_name=festival["title"],
                            reason="duplicate", proposed_value=proposal, approval_status="pending", created_at=now,
                        )
                        self._write_history(festival_id, {}, {"duplicate_submission": {"queue_id": queue_id}},
                                            request.reason, actor, now)
                    raise duplicate_error()
            festival_id = f"fst_{ULID()}"
            changes = {**values, "review_status": "pending"}
            self._festivals[festival_id] = {
                **self._empty_fields, **changes, "published_at": None,
                "source": "admin", "source_ref": festival_id, "last_synced_at": now.isoformat(),
            }
            self._write_history(festival_id, {}, changes, request.reason, actor, now)
            return FestivalRegistrationResult(festival_id=festival_id)

    def update(self, festival_id: str, request: FestivalUpdate, actor: UUID) -> FestivalUpdateResult:
        with self._lock:
            festival = self._festivals.get(festival_id)
            if festival is None:
                raise missing_festival()
            now = datetime.now(timezone.utc)
            changes = update_fields(request, festival, now)
            self._write_history(festival_id, festival, changes, request.reason, actor, now)
            self._apply_changes(festival_id, changes)
            return update_result(festival_id, festival)

    def _apply_changes(self, festival_id: str, changes: dict[str, object]) -> None:
        super()._apply_changes(festival_id, changes)
        festival = self._festivals[festival_id]
        if "source" not in festival:
            return
        if festival["review_status"] == "approved" and festival["published_at"] is not None:
            self.catalog[festival_id] = self._public_detail(festival_id, festival)
        else:
            self.catalog.pop(festival_id, None)

    def public_festivals(self) -> list[MockFestival]:
        with self._lock:
            return [festival for festival in self.catalog.values() if festival.category == FESTIVAL_CATEGORY]

    def public_festival(self, festival_id: str) -> MockFestival | None:
        with self._lock:
            festival = self.catalog.get(festival_id)
            return festival if festival and festival.category == FESTIVAL_CATEGORY else None

    @staticmethod
    def _public_detail(festival_id: str, festival: dict[str, object]) -> MockFestival:
        has_image = festival["image_url"] or festival["thumbnail_url"]
        credit = (ADMIN_IMAGE_CREDIT if festival["source"] == "admin" else "한국관광공사") if has_image else None
        kind = festival["image_copyright_type"]
        return MockFestival(
            festival_id=festival_id, category=festival["category"], name=festival["title"],
            region_code=festival["region_code"], venue_name=festival["venue_name"], address=festival["address"],
            lat=festival["latitude"], lng=festival["longitude"], start_date=festival["start_date"],
            end_date=festival["end_date"], event_status=festival["event_status"],
            overview=festival["summary"] or "", fee_text=festival["admission_fee_text"],
            homepage_url=festival["official_url"], image_url=festival["image_url"],
            thumbnail_url=festival["thumbnail_url"], image_credit=credit,
            image_copyright=(
                {"type": kind, "credit": credit, "modify_allowed": kind == "Type1"} if credit and kind else None
            ),
            source=festival["source"], source_ref=festival["source_ref"], last_synced_at=festival["last_synced_at"],
        )


mock_festival_store = MemoryAdminFestivalStore()
