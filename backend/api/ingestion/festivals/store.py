from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import Connection, Engine, column, func, select, table
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.exc import DataError, IntegrityError
from ulid import ULID

from api.ingestion.festivals.normalize import KST, FestivalRecord

SOURCE_ID = "tourapi"
DETAIL_FIELDS = ("venue_name", "summary", "admission_fee_text", "official_url", "organizer")
FESTIVAL_FIELDS = (
    "title", "start_date", "end_date", "address", "latitude", "longitude", "region_code",
    "category", "image_url", "thumbnail_url", "image_copyright_type", "event_status",
    "source_updated_at", *DETAIL_FIELDS,
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
    "festival_change_history", column("festival_id"), column("field"),
    column("before_value", JSONB), column("after_value", JSONB), column("source_id"),
    column("actor"), column("changed_at"),
)
SOURCE_FESTIVALS = FESTIVAL_SOURCES.join(
    FESTIVALS, FESTIVAL_SOURCES.c.festival_id == FESTIVALS.c.festival_id
)

FieldValue = str | date | Decimal | None
ErrorEntry = dict[str, str | None]
UpsertAction = Literal["inserted", "unchanged", "updated"]


@dataclass(frozen=True)
class StoredFestival:
    source_updated_at: datetime | None
    raw_checksum: str
    details: dict[str, str | None]


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
    elif record.publishable:
        values.update(review_status="approved", published_at=previous.get("published_at") or now)
    else:
        values.update(review_status="pending", published_at=None)
    return values


def changed_fields(
    previous: Mapping[str, FieldValue], values: Mapping[str, FieldValue]
) -> dict[str, FieldValue]:
    return {name: value for name, value in values.items() if previous[name] != value}


def _json_value(value: FieldValue) -> str | float | None:
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


def _upsert(
    connection: Connection, record: FestivalRecord, job_id: str, now: datetime
) -> UpsertAction:
    source = (FESTIVAL_SOURCES.c.source_id == SOURCE_ID) & (
        FESTIVAL_SOURCES.c.source_item_id == record.source_item_id
    )
    previous = connection.execute(
        select(FESTIVALS, FESTIVAL_SOURCES.c.raw_checksum)
        .select_from(SOURCE_FESTIVALS).where(source).with_for_update(of=FESTIVALS)
    ).mappings().one_or_none()
    action = upsert_action(previous["raw_checksum"] if previous else None, record.raw_checksum)
    sync = {"fetched_at": now, "last_job_id": job_id}
    if previous is None:
        festival_id = f"fst_{ULID()}"
        connection.execute(FESTIVALS.insert().values(
            festival_id=festival_id, collected_at=now, last_synced_at=now,
            **festival_values(record, {}, now),
        ))
        connection.execute(FESTIVAL_SOURCES.insert().values(
            festival_id=festival_id, source_id=SOURCE_ID, source_item_id=record.source_item_id,
            raw_checksum=record.raw_checksum, **sync,
        ))
        return action

    festival_id = previous["festival_id"]
    saved_version = previous["source_updated_at"]
    if saved_version is not None and (
        record.source_updated_at is None or record.source_updated_at < saved_version
    ):
        action = "unchanged"
    changes = {}
    if action == "updated":
        changes = changed_fields(previous, festival_values(record, previous, now))
        sync["raw_checksum"] = record.raw_checksum
    connection.execute(FESTIVALS.update().where(FESTIVALS.c.festival_id == festival_id).values(
        last_synced_at=now, **changes,
    ))
    connection.execute(FESTIVAL_SOURCES.update().where(source).values(**sync))
    if changes:
        _write_history(connection, festival_id, previous, changes, now)
    return action


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
    ) -> JobResult:
        job_errors = errors.copy()
        job_filter = INGESTION_JOBS.c.job_id == job_id
        with self.engine.begin() as connection:
            previous = connection.execute(
                select(INGESTION_JOBS).where(job_filter).with_for_update()
            ).mappings().one()
            if previous["status"] != "running":
                errors[:] = previous["error"] or []
                return JobResult(job_id, previous["status"], previous["scanned"], previous["inserted"],
                                 previous["updated"], previous["rejected"])
            counts = Counter() if failed else self._save_records(
                connection, job_id, records, job_errors, redact,
            )
            ended_at = datetime.now(KST)
            status = "failed" if failed else "partial" if job_errors else "success"
            result = JobResult(
                job_id, status, len(records), counts["inserted"], counts["updated"], counts["rejected"],
            )
            connection.execute(INGESTION_JOBS.update().where(job_filter).values(
                status=status, scanned=result.scanned, inserted=result.inserted, updated=result.updated,
                rejected=result.rejected, ended_at=ended_at, error=job_errors or None,
            ))
            if status == "success":
                connection.execute(DATA_SOURCES.update().where(DATA_SOURCES.c.source_id == SOURCE_ID).values(
                    last_success_at=func.greatest(DATA_SOURCES.c.last_success_at, ended_at),
                ))
        errors[:] = job_errors
        return result

    def _save_records(
        self,
        connection: Connection,
        job_id: str,
        records: Sequence[FestivalRecord],
        errors: list[ErrorEntry],
        redact: Callable[[str], str],
    ) -> Counter[str]:
        # 같은 출처의 저장을 직렬화해 아직 없는 contentid도 중복 삽입되지 않게 한다.
        connection.execute(select(DATA_SOURCES.c.source_id).where(
            DATA_SOURCES.c.source_id == SOURCE_ID,
        ).with_for_update(key_share=True)).scalar_one()
        now = datetime.now(KST)
        counts: Counter[str] = Counter()
        for record in records:
            if not record.source_item_id or not record.title or not record.region_code:
                code = "DB_REQUIRED_FIELD"
            else:
                try:
                    with connection.begin_nested():
                        action = _upsert(connection, record, job_id, now)
                except (DataError, IntegrityError):
                    code = "DB_INVALID_RECORD"
                else:
                    counts[action] += 1
                    continue
            counts["rejected"] += 1
            errors.append({"content_id": redact(record.source_item_id), "stage": "db_save", "code": code})
        return counts


def _to_kst(value: datetime | None) -> datetime | None:
    """DB가 돌려준 시각(UTC 표기)을 수집 결과와 같은 한국 시간 표기로 맞춘다."""
    return value.astimezone(KST) if value is not None else None
