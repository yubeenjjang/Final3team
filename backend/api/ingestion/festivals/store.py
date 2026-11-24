from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import Connection, Engine, column, func, select, table
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.sql.selectable import ScalarSelect
from ulid import ULID

from api.ingestion.festivals.admin_edits import DATE_FIELDS, protect_admin_edits
from api.ingestion.festivals.normalize import (
    CLASS_UNVERIFIED, COORDS_OUT_OF_RANGE, FESTIVAL_CATEGORY, FESTIVAL_CLASS, KST, NOT_FESTIVAL_CLASS,
    FestivalRecord,
)

SOURCE_ID = "tourapi"
PRESENCE_FIELD = "source_presence"
MISSING = "missing_from_source"
REAPPEARED = "reappeared_in_source"
CLASSIFICATION_FIELD = "source_classification"
CLASSIFICATION_FIELDS = ("category", "source_class_level1", "source_class_level2", "source_class_code")
PUBLICATION_FIELDS = ("review_status", "published_at")
LOCATION_FIELDS = ("address", "latitude", "longitude", "coords_source")
DETAIL_FIELDS = ("venue_name", "summary", "admission_fee_text", "official_url", "organizer")
FESTIVAL_FIELDS = (
    "title", "start_date", "end_date", *LOCATION_FIELDS, "region_code",
    "image_url", "thumbnail_url", "image_copyright_type", "event_status",
    "source_updated_at", *CLASSIFICATION_FIELDS, *DETAIL_FIELDS,
)

DATA_SOURCES = table(
    "data_sources", column("source_id"), column("name"), column("provider_org"),
    column("scope"), column("is_realtime"), column("refresh_s"), column("key_site"),
    column("status"), column("last_success_at"),
)
INGESTION_JOBS = table(
    "ingestion_jobs", column("job_id"), column("source_id"), column("started_at"),
    column("ended_at"), column("status"), column("scanned"), column("inserted"),
    column("updated"), column("rejected"), column("error", JSONB(none_as_null=True)),
)
FESTIVAL_SOURCES = table(
    "festival_sources", column("festival_id"), column("source_id"), column("source_item_id"),
    column("raw_checksum"), column("fetched_at"), column("last_job_id"),
)
FESTIVALS = table(
    "festivals", *(column(name) for name in FESTIVAL_FIELDS), column("festival_id"),
    column("review_status"), column("published_at"), column("collected_at"), column("last_synced_at"),
)
FESTIVAL_CHANGE_HISTORY = table(
    "festival_change_history", column("change_id"), column("festival_id"), column("field"),
    column("before_value", JSONB), column("after_value", JSONB), column("source_id"),
    column("actor"), column("changed_at"),
)
FESTIVAL_REVIEW_QUEUE = table(
    "festival_review_queue", column("festival_id"), column("reason"), column("approval_status"),
)
SOURCE_FESTIVALS = FESTIVAL_SOURCES.join(
    FESTIVALS, FESTIVAL_SOURCES.c.festival_id == FESTIVALS.c.festival_id
)

FieldValue = str | date | Decimal | dict[str, str] | None
ErrorEntry = dict[str, str | None]
UpsertAction = Literal["inserted", "unchanged", "updated"]


@dataclass(frozen=True)
class StoredFestival:
    source_updated_at: datetime | None
    raw_checksum: str
    details: dict[str, str | None]


@dataclass(frozen=True)
class ListingScope:
    since: date
    until: date | None

    def as_json(self) -> dict[str, str | None]:
        return {
            "endpoint": "searchFestival2", "region": "national",
            "since": self.since.isoformat(), "until": self.until.isoformat() if self.until else None,
        }


@dataclass(frozen=True)
class JobResult:
    job_id: str
    status: str
    scanned: int
    inserted: int
    updated: int
    rejected: int


def upsert_action(previous_checksum: str | None, raw_checksum: str) -> UpsertAction:
    if previous_checksum is None:
        return "inserted"
    return "unchanged" if previous_checksum == raw_checksum else "updated"


def festival_values(
    record: FestivalRecord, previous: Mapping[str, FieldValue], now: datetime
) -> dict[str, FieldValue]:
    values = {name: getattr(record, name) for name in FESTIVAL_FIELDS}
    for name in ("latitude", "longitude"):
        if values[name] is not None:
            values[name] = Decimal(str(values[name]))

    if previous.get("review_status") == "hidden":
        values.update(review_status="hidden", published_at=previous["published_at"])
    elif (
        record.category == FESTIVAL_CATEGORY and record.source_class_level2 == FESTIVAL_CLASS
        and record.publishable
    ):
        values.update(review_status="approved", published_at=previous.get("published_at") or now)
    else:
        values.update(review_status="pending", published_at=None)
    return values


def changed_fields(
    previous: Mapping[str, FieldValue], values: Mapping[str, FieldValue]
) -> dict[str, FieldValue]:
    return {name: value for name, value in values.items() if previous[name] != value}


def _json_value(value: FieldValue) -> str | float | dict[str, str] | None:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _write_history(
    connection: Connection,
    festival_id: str,
    previous: Mapping[str, FieldValue],
    changes: Mapping[str, FieldValue],
    now: datetime,
) -> None:
    connection.execute(FESTIVAL_CHANGE_HISTORY.insert(), [
        {
            "festival_id": festival_id,
            "field": name,
            "before_value": _json_value(previous[name]),
            "after_value": _json_value(value),
            "source_id": SOURCE_ID,
            "actor": "ingestion",
            "changed_at": now,
        }
        for name, value in changes.items()
    ])


def _queue_review(connection: Connection, festival_id: str, reason: str) -> None:
    # 호출자가 축제 행을 잠근 상태에서 같은 사유의 미처리 건을 확인한다.
    pending = select(FESTIVAL_REVIEW_QUEUE.c.reason).where(
        FESTIVAL_REVIEW_QUEUE.c.festival_id == festival_id,
        FESTIVAL_REVIEW_QUEUE.c.reason == reason,
        FESTIVAL_REVIEW_QUEUE.c.approval_status == "pending",
    )
    if not connection.execute(select(pending.exists())).scalar_one():
        connection.execute(FESTIVAL_REVIEW_QUEUE.insert().values(festival_id=festival_id, reason=reason))


def _quality_review_reason(values: Mapping[str, FieldValue]) -> str | None:
    if values.get("review_status") != "pending":
        return None
    level2 = values["source_class_level2"]
    if not level2 or not str(level2).strip():
        return CLASS_UNVERIFIED
    if level2 != FESTIVAL_CLASS:
        return NOT_FESTIVAL_CLASS
    if values["address"] and (values["latitude"] is None or values["longitude"] is None):
        return COORDS_OUT_OF_RANGE
    return None


def _record_presence(
    connection: Connection, festival_id: str, job_id: str, reason: str, now: datetime,
    previous: dict[str, str] | None = None,
) -> None:
    _write_history(
        connection, festival_id, {PRESENCE_FIELD: previous},
        {PRESENCE_FIELD: {"reason": reason, "job_id": job_id}}, now,
    )
    if reason == MISSING:
        _queue_review(connection, festival_id, reason)


def _record_classification(
    connection: Connection, festival_id: str, job_id: str, reason: str, now: datetime,
) -> None:
    _write_history(
        connection, festival_id, {CLASSIFICATION_FIELD: None},
        {CLASSIFICATION_FIELD: {"reason": reason, "job_id": job_id}}, now,
    )


def _last_presence() -> ScalarSelect[dict[str, str]]:
    return select(FESTIVAL_CHANGE_HISTORY.c.after_value).where(
        FESTIVAL_CHANGE_HISTORY.c.festival_id == FESTIVALS.c.festival_id,
        FESTIVAL_CHANGE_HISTORY.c.source_id == SOURCE_ID,
        FESTIVAL_CHANGE_HISTORY.c.field == PRESENCE_FIELD,
    ).order_by(FESTIVAL_CHANGE_HISTORY.c.change_id.desc()).limit(1).scalar_subquery()


def _upsert(
    connection: Connection, record: FestivalRecord, job_id: str, started_at: datetime, now: datetime,
) -> UpsertAction | None:
    source = (FESTIVAL_SOURCES.c.source_id == SOURCE_ID) & (
        FESTIVAL_SOURCES.c.source_item_id == record.source_item_id
    )
    last_started = select(INGESTION_JOBS.c.started_at).where(
        INGESTION_JOBS.c.job_id == FESTIVAL_SOURCES.c.last_job_id,
    ).scalar_subquery()
    previous = connection.execute(
        select(FESTIVALS, FESTIVAL_SOURCES.c.raw_checksum, _last_presence().label("source_presence"),
               last_started.label("last_job_started_at"))
        .select_from(SOURCE_FESTIVALS).where(source).with_for_update(of=FESTIVALS)
    ).mappings().one_or_none()
    action = upsert_action(previous["raw_checksum"] if previous else None, record.raw_checksum)
    has_required_fields = bool(record.title and record.region_code)
    sync = {"fetched_at": now, "last_job_id": job_id}
    if previous is None:
        if not has_required_fields:
            return None
        festival_id = f"fst_{ULID()}"
        values = festival_values(record, {}, now)
        connection.execute(FESTIVALS.insert().values(
            festival_id=festival_id, collected_at=now, last_synced_at=now, **values,
        ))
        review_reason = _quality_review_reason(values)
        if review_reason:
            _queue_review(connection, festival_id, review_reason)
        connection.execute(FESTIVAL_SOURCES.insert().values(
            festival_id=festival_id, source_id=SOURCE_ID, source_item_id=record.source_item_id,
            raw_checksum=record.raw_checksum, **sync,
        ))
        return action

    if previous["last_job_started_at"] and previous["last_job_started_at"] > started_at:
        return "unchanged"
    if not has_required_fields and record.category == FESTIVAL_CATEGORY:
        return None

    festival_id = previous["festival_id"]
    saved_version = previous["source_updated_at"]
    version_is_current = saved_version is None or (
        record.source_updated_at is not None and record.source_updated_at >= saved_version
    )
    refresh_fields = action == "updated" and has_required_fields and version_is_current
    values = festival_values(record, previous, now)
    if previous["source_presence"] and previous["review_status"] == "pending":
        values.update(review_status="pending", published_at=None)
    if refresh_fields:
        sync["raw_checksum"] = record.raw_checksum
    else:
        # 목록 분류는 상세 재요청·체크섬과 별개로 갱신한다.
        fields = CLASSIFICATION_FIELDS
        listing_is_current = (
            saved_version is None or record.listing_updated_at is None
            or record.listing_updated_at >= saved_version
        )
        # 같은 목록을 재수집해도 좌표 보정과 주소 없는 축제의 공개 판정을 반영한다.
        recheck_location = has_required_fields and listing_is_current and (
            COORDS_OUT_OF_RANGE in record.issues
            or any(previous[name] != values[name] for name in LOCATION_FIELDS)
        )
        if recheck_location:
            fields += LOCATION_FIELDS
        if (
            recheck_location or record.source_class_level2 != FESTIVAL_CLASS
            or previous["source_class_level2"] != record.source_class_level2
            or previous["category"] != record.category
        ):
            fields += PUBLICATION_FIELDS
            location = values if recheck_location else previous
            if values["review_status"] == "approved" and (
                previous["start_date"] is None or previous["end_date"] is None
                or (
                    location["address"] is not None
                    and (location["latitude"] is None or location["longitude"] is None)
                )
            ):
                values.update(review_status="pending", published_at=None)
        values = {name: values[name] for name in fields}
    changes = changed_fields(previous, values)
    conflicts = protect_admin_edits(connection, festival_id, previous, changes)
    if (
        conflicts.intersection((*LOCATION_FIELDS, *DATE_FIELDS)) and "review_status" in values
        and previous["review_status"] != "hidden"
        and not (previous["source_presence"] and previous["review_status"] == "pending")
    ):
        # 게시 판단은 수집 제안 대신 실제로 저장될 날짜·위치와 분류를 사용합니다.
        effective = {**previous, **changes}
        valid_location = effective["address"] is None or (
            effective["latitude"] is not None and effective["longitude"] is not None
        )
        publishable = (
            effective["category"] == FESTIVAL_CATEGORY and effective["source_class_level2"] == FESTIVAL_CLASS
            and effective["start_date"] is not None and effective["end_date"] is not None and valid_location
        )
        for field in PUBLICATION_FIELDS:
            changes.pop(field, None)
        changes.update(changed_fields(previous, {
            "review_status": "approved" if publishable else "pending",
            "published_at": (previous["published_at"] or now) if publishable else None,
        }))
    if not has_required_fields and not changes:
        return None
    connection.execute(FESTIVALS.update().where(FESTIVALS.c.festival_id == festival_id).values(
        last_synced_at=now, **changes,
    ))
    connection.execute(FESTIVAL_SOURCES.update().where(source).values(**sync))
    if changes:
        _write_history(connection, festival_id, previous, changes, now)
        review_reason = _quality_review_reason({**previous, **changes})
        if review_reason and review_reason != _quality_review_reason(previous):
            _queue_review(connection, festival_id, review_reason)
    if (record.source_class_level2 != FESTIVAL_CLASS and previous["review_status"] == "approved"
            and previous["published_at"] is not None and changes.get("review_status") == "pending"):
        reason = CLASS_UNVERIFIED if record.source_class_level2 is None else NOT_FESTIVAL_CLASS
        _record_classification(connection, festival_id, job_id, reason, now)
    return "updated" if refresh_fields or changes else "unchanged"


class FestivalStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def start_job(self, started_at: datetime) -> str:
        job_id = f"ij_{ULID()}"
        with self.engine.begin() as connection:
            connection.execute(insert(DATA_SOURCES).values(
                source_id=SOURCE_ID, name="한국관광공사 TourAPI", provider_org="한국관광공사",
                scope="national", is_realtime=False, refresh_s=86400, key_site="data.go.kr",
                status="verified",
            ).on_conflict_do_nothing(index_elements=[DATA_SOURCES.c.source_id]))
            connection.execute(INGESTION_JOBS.insert().values(
                job_id=job_id, source_id=SOURCE_ID, started_at=started_at, status="running",
            ))
        return job_id

    def load(self, source_item_ids: Collection[str]) -> dict[str, StoredFestival]:
        if not source_item_ids:
            return {}
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    FESTIVAL_SOURCES.c.source_item_id, FESTIVAL_SOURCES.c.raw_checksum,
                    FESTIVALS.c.source_updated_at, *(FESTIVALS.c[name] for name in DETAIL_FIELDS),
                ).select_from(SOURCE_FESTIVALS).where(
                    FESTIVAL_SOURCES.c.source_id == SOURCE_ID,
                    FESTIVAL_SOURCES.c.source_item_id.in_(source_item_ids),
                )
            ).mappings()
            return {
                row["source_item_id"]: StoredFestival(
                    _to_kst(row["source_updated_at"]), row["raw_checksum"],
                    {name: row[name] for name in DETAIL_FIELDS},
                )
                for row in rows
            }

    def finish_job(
        self,
        job_id: str,
        records: Sequence[FestivalRecord],
        errors: list[ErrorEntry],
        *,
        failed: bool = False,
        redact: Callable[[str], str] = str,
        scope: ListingScope | None = None,
    ) -> JobResult:
        job_errors = errors.copy()
        job_filter = INGESTION_JOBS.c.job_id == job_id
        with self.engine.begin() as connection:
            previous = connection.execute(
                select(INGESTION_JOBS).where(job_filter).with_for_update()
            ).mappings().one()
            if previous["status"] != "running":
                saved = previous["error"]
                errors[:] = saved["errors"] if isinstance(saved, dict) else saved or []
                return JobResult(job_id, previous["status"], previous["scanned"], previous["inserted"],
                                 previous["updated"], previous["rejected"])
            track_presence = not failed and self._is_current_job(connection, previous["started_at"])
            counts = Counter() if failed else self._save_records(
                connection, job_id, previous["started_at"], records, job_errors, redact,
            )
            ended_at = datetime.now(KST)
            status = "failed" if failed else "partial" if job_errors else "success"
            job_data = job_errors or None
            seen = {record.source_item_id for record in records if record.source_item_id}
            if track_presence and seen:
                self._mark_reappeared(connection, job_id, seen, ended_at)
            if track_presence and status == "success":
                self._mark_unverified(connection, job_id, ended_at)
            if track_presence and status == "success" and scope is not None:
                self._mark_missing(connection, job_id, scope, seen, ended_at)
                job_data = {
                    "errors": job_errors,
                    "listing": {"scope": scope.as_json(), "ids": sorted({redact(item) for item in seen})},
                }
            result = JobResult(
                job_id, status, len(records), counts["inserted"], counts["updated"], counts["rejected"],
            )
            connection.execute(INGESTION_JOBS.update().where(job_filter).values(
                status=status, scanned=result.scanned, inserted=result.inserted, updated=result.updated,
                rejected=result.rejected, ended_at=ended_at, error=job_data,
            ))
            if status == "success":
                connection.execute(DATA_SOURCES.update().where(DATA_SOURCES.c.source_id == SOURCE_ID).values(
                    last_success_at=func.greatest(DATA_SOURCES.c.last_success_at, ended_at),
                ))
        errors[:] = job_errors
        return result

    def _is_current_job(self, connection: Connection, started_at: datetime) -> bool:
        # 같은 공급원의 업서트와 누락 판단을 함께 직렬화한다.
        connection.execute(select(DATA_SOURCES.c.source_id).where(
            DATA_SOURCES.c.source_id == SOURCE_ID,
        ).with_for_update(key_share=True)).scalar_one()
        newer = select(INGESTION_JOBS.c.job_id).where(
            INGESTION_JOBS.c.source_id == SOURCE_ID,
            INGESTION_JOBS.c.status.in_(("success", "partial")),
            INGESTION_JOBS.c.started_at > started_at,
        )
        return not connection.execute(select(newer.exists())).scalar_one()

    def _mark_unverified(self, connection: Connection, job_id: str, now: datetime) -> None:
        # 목록에서 빠진 014 이전 공개 행에도 분류 검증 기준을 적용한다.
        rows = connection.execute(select(
            FESTIVALS.c.festival_id, FESTIVALS.c.review_status, FESTIVALS.c.published_at,
        ).where(
            FESTIVALS.c.category == FESTIVAL_CATEGORY,
            FESTIVALS.c.review_status == "approved",
            FESTIVALS.c.published_at.is_not(None),
            func.nullif(func.btrim(FESTIVALS.c.source_class_level2), "").is_(None),
        ).with_for_update()).mappings()
        changes = {"review_status": "pending", "published_at": None}
        for row in rows:
            festival_id = row["festival_id"]
            connection.execute(FESTIVALS.update().where(
                FESTIVALS.c.festival_id == festival_id,
            ).values(**changes))
            _write_history(connection, festival_id, row, changes, now)
            _record_classification(connection, festival_id, job_id, CLASS_UNVERIFIED, now)

    def _mark_missing(
        self, connection: Connection, job_id: str, scope: ListingScope, seen: set[str], now: datetime,
    ) -> None:
        listing = INGESTION_JOBS.c.error["listing"]
        previous_ids = connection.execute(
            select(listing["ids"]).where(
                INGESTION_JOBS.c.source_id == SOURCE_ID,
                INGESTION_JOBS.c.status == "success",
                listing["scope"] == scope.as_json(),
            ).order_by(INGESTION_JOBS.c.started_at.desc(), INGESTION_JOBS.c.job_id.desc()).limit(1)
        ).scalar_one_or_none()
        missing = set(previous_ids or ()) - seen
        if not missing:
            return
        sources = FESTIVAL_SOURCES.alias("seen_sources")
        still_listed = select(sources.c.source_item_id).where(
            sources.c.festival_id == FESTIVALS.c.festival_id,
            sources.c.source_id == SOURCE_ID,
            sources.c.source_item_id.in_(seen),
        ).exists()
        candidates = select(FESTIVALS).select_from(SOURCE_FESTIVALS).where(
            FESTIVAL_SOURCES.c.source_id == SOURCE_ID,
            FESTIVAL_SOURCES.c.source_item_id.in_(missing),
            ~still_listed,
            FESTIVALS.c.start_date >= scope.since,
            FESTIVALS.c.category == FESTIVAL_CATEGORY,
            FESTIVALS.c.review_status == "approved",
            FESTIVALS.c.published_at.is_not(None),
        )
        if scope.until is not None:
            candidates = candidates.where(FESTIVALS.c.start_date <= scope.until)
        rows = connection.execute(candidates.with_for_update(of=FESTIVALS)).mappings().unique()
        changes = {"review_status": "pending", "published_at": None}
        for row in rows:
            festival_id = row["festival_id"]
            connection.execute(FESTIVALS.update().where(
                FESTIVALS.c.festival_id == festival_id,
            ).values(**changes))
            _write_history(connection, festival_id, row, changes, now)
            _record_presence(connection, festival_id, job_id, MISSING, now)

    def _mark_reappeared(
        self, connection: Connection, job_id: str, seen: set[str], now: datetime,
    ) -> None:
        presence = _last_presence()
        rows = connection.execute(
            select(FESTIVALS.c.festival_id, presence).select_from(SOURCE_FESTIVALS).where(
                FESTIVAL_SOURCES.c.source_id == SOURCE_ID,
                FESTIVAL_SOURCES.c.source_item_id.in_(seen),
                presence["reason"].astext == MISSING,
            ).distinct()
        )
        for festival_id, previous in rows:
            _record_presence(connection, festival_id, job_id, REAPPEARED, now, previous)

    def _save_records(
        self,
        connection: Connection,
        job_id: str,
        started_at: datetime,
        records: Sequence[FestivalRecord],
        errors: list[ErrorEntry],
        redact: Callable[[str], str],
    ) -> Counter[str]:
        now = datetime.now(KST)
        counts: Counter[str] = Counter()
        for record in records:
            if not record.source_item_id:
                code = "DB_REQUIRED_FIELD"
            else:
                try:
                    with connection.begin_nested():
                        action = _upsert(connection, record, job_id, started_at, now)
                except (DataError, IntegrityError):
                    code = "DB_INVALID_RECORD"
                else:
                    if action is not None and record.title and record.region_code:
                        counts[action] += 1
                        continue
                    code = "DB_REQUIRED_FIELD"
            counts["rejected"] += 1
            errors.append({"content_id": redact(record.source_item_id), "stage": "db_save", "code": code})
        return counts


def _to_kst(value: datetime | None) -> datetime | None:
    """DB가 돌려준 시각(UTC 표기)을 수집 결과와 같은 한국 시간 표기로 맞춘다."""
    return value.astimezone(KST) if value is not None else None
