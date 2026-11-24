from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert
from ulid import ULID

from api.ingestion.festivals.admin_edits import protect_admin_edits
from api.ingestion.festivals.normalize import FESTIVAL_CATEGORY, FESTIVAL_CLASS, KST
from api.ingestion.festivals.store import (
    DATA_SOURCES, FESTIVAL_REVIEW_QUEUE, FESTIVAL_SOURCES, FESTIVALS, INGESTION_JOBS,
    SOURCE_ID as TOURAPI_SOURCE_ID, ErrorEntry, JobResult, _write_history,
)
from api.ingestion.seoul_culture.normalize import SOURCE_ID, SUPPLEMENT_FIELDS, SeoulFestival, normalized_title
from api.providers.transit_arrivals import distance_m

_F = FESTIVALS.c
_S = FESTIVAL_SOURCES.c
_SEOUL_SOURCE = DATA_SOURCES.c.source_id == SOURCE_ID
_HAS_TOURAPI = select(_S.festival_id).where(
    _S.festival_id == _F.festival_id, _S.source_id == TOURAPI_SOURCE_ID,
).correlate(FESTIVALS).exists()


def _date_and_title_match(event: SeoulFestival, row: Mapping) -> bool:
    return (
        row["region_code"] == "SEOUL"
        and row["category"] == FESTIVAL_CATEGORY
        and row["source_class_level2"] == FESTIVAL_CLASS
        and row["start_date"] is not None and row["end_date"] is not None
        and row["start_date"] <= event.end_date and row["end_date"] >= event.start_date
        and normalized_title(row["title"]) == normalized_title(event.title)
    )


def _nearby(event: SeoulFestival, row: Mapping) -> bool | None:
    coords = (event.latitude, event.longitude, row["latitude"], row["longitude"])
    if any(value is None for value in coords):
        return None
    return distance_m(*(float(value) for value in coords)) <= 500


def _match(connection: Connection, event: SeoulFestival) -> tuple[Mapping | None, str]:
    candidates = connection.execute(select(
        _F.festival_id, _F.title, _F.region_code, _F.category, _F.source_class_level2,
        _F.start_date, _F.end_date, _F.latitude, _F.longitude,
    ).where(
        _F.region_code == "SEOUL", _F.category == FESTIVAL_CATEGORY, _F.source_class_level2 == FESTIVAL_CLASS,
        _F.start_date <= event.end_date, _F.end_date >= event.start_date, _HAS_TOURAPI,
    )).mappings()
    possible = [
        (row["festival_id"], _nearby(event, row)) for row in candidates if _date_and_title_match(event, row)
    ]
    close = [match for match in possible if match[1] is not False]
    if len(close) == 1 and close[0][1] is True:
        # A55·A56 및 A24가 같은 축제를 바꿀 수 있으므로 갱신 직전에 일치 여부를 다시 확인한다.
        row = connection.execute(select(FESTIVALS).where(
            _F.festival_id == close[0][0], _HAS_TOURAPI,
        ).with_for_update(key_share=True)).mappings().one_or_none()
        if row is not None and _date_and_title_match(event, row) and _nearby(event, row):
            return row, "duplicate"
    return None, "duplicate" if possible else "class_unverified"


def _quarantine(connection: Connection, event: SeoulFestival, reason: str, now: datetime) -> str:
    festival_id = f"fst_{ULID()}"
    connection.execute(FESTIVALS.insert().values(
        festival_id=festival_id, title=event.title, region_code="SEOUL", category=FESTIVAL_CATEGORY,
        start_date=event.start_date, end_date=event.end_date, venue_name=event.venue_name,
        latitude=event.latitude, longitude=event.longitude, event_status=event.event_status,
        official_url=event.official_url, admission_fee_text=event.admission_fee_text,
        review_status="pending", collected_at=now, last_synced_at=now,
    ))
    connection.execute(FESTIVAL_REVIEW_QUEUE.insert().values(
        festival_id=festival_id, reason=reason,
        proposed_value={
            "start_date": event.start_date.isoformat(), "end_date": event.end_date.isoformat(),
            "venue_name": event.venue_name, "latitude": event.latitude, "longitude": event.longitude,
            "official_url": event.official_url, "admission_fee_text": event.admission_fee_text,
        },
    ))
    return festival_id


def _fill_gaps(
    connection: Connection, festival: Mapping, event: SeoulFestival, now: datetime, *, source_changed: bool,
) -> bool:
    festival_id = festival["festival_id"]
    changes = {
        field: getattr(event, field) for field in SUPPLEMENT_FIELDS
        if not (festival[field] or "").strip() and getattr(event, field)
    }
    protect_admin_edits(connection, festival_id, festival, changes, queue_conflicts=source_changed)
    if not changes:
        return False
    connection.execute(FESTIVALS.update().where(_F.festival_id == festival_id).values(
        last_synced_at=now, **changes,
    ))
    _write_history(connection, festival_id, festival, changes, now, source_id=SOURCE_ID)
    return True


def _save_event(connection: Connection, event: SeoulFestival, job_id: str, now: datetime) -> str:
    source = (_S.source_id == SOURCE_ID) & (_S.source_item_id == event.source_item_id)
    existing = connection.execute(
        select(_S.festival_id, _S.raw_checksum, _HAS_TOURAPI.label("linked_to_tourapi"))
        .select_from(FESTIVAL_SOURCES.join(FESTIVALS, _F.festival_id == _S.festival_id)).where(source)
    ).mappings().one_or_none()
    source_changed = existing is None or existing["raw_checksum"] != event.raw_checksum
    fields_changed = False
    festival_id = existing["festival_id"] if existing else None

    # 격리 후에는 처리 결정과 기존 연결을 보존하고, 확정 병합된 연결의 동일성이 바뀌면 보강을 보류한다.
    if existing is None or existing["linked_to_tourapi"]:
        matched, reason = _match(connection, event)
        if existing is None and matched is None:
            festival_id = _quarantine(connection, event, reason, now)
        elif matched is not None and (existing is None or matched["festival_id"] == festival_id):
            festival_id = matched["festival_id"]
            fields_changed = _fill_gaps(connection, matched, event, now, source_changed=source_changed)

    sync = {"fetched_at": now, "last_job_id": job_id}
    if source_changed:
        sync.update(raw_checksum=event.raw_checksum, source_url=event.source_url, source_image_url=event.source_image_url)
    if existing is None:
        connection.execute(FESTIVAL_SOURCES.insert().values(
            festival_id=festival_id, source_id=SOURCE_ID, source_item_id=event.source_item_id, **sync,
        ))
        return "inserted" if matched is None else "updated"
    connection.execute(FESTIVAL_SOURCES.update().where(source).values(**sync))
    return "updated" if source_changed or fields_changed else "unchanged"


class SeoulCultureStore:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def start_job(self, started_at: datetime) -> str:
        job_id = f"ij_{ULID()}"
        with self.engine.begin() as connection:
            connection.execute(insert(DATA_SOURCES).values(
                source_id=SOURCE_ID, name="서울시 문화행사 정보", provider_org="서울특별시",
                scope="seoul_only", is_realtime=False, refresh_s=86400, key_site="data.seoul.go.kr",
                status="verified",
            ).on_conflict_do_nothing(index_elements=[DATA_SOURCES.c.source_id]))
            connection.execute(INGESTION_JOBS.insert().values(
                job_id=job_id, source_id=SOURCE_ID, started_at=started_at, status="running",
            ))
        return job_id

    def finish_job(
        self, job_id: str, events: Sequence[SeoulFestival], scanned: int, errors: list[ErrorEntry], *,
        failed: bool = False,
    ) -> JobResult:
        with self.engine.begin() as connection:
            # 같은 공급원의 동일 원본을 동시에 처리해도 축제·출처·검토 항목을 한 번만 만든다.
            connection.execute(select(DATA_SOURCES.c.source_id).where(_SEOUL_SOURCE)
                               .with_for_update(key_share=True)).scalar_one()
            job = (INGESTION_JOBS.c.job_id == job_id) & (INGESTION_JOBS.c.source_id == SOURCE_ID)
            previous = connection.execute(select(INGESTION_JOBS).where(job)).mappings().one()
            if previous["status"] != "running":
                return JobResult(job_id, previous["status"], previous["scanned"], previous["inserted"],
                                 previous["updated"], previous["rejected"])
            now = datetime.now(KST)
            counts = Counter(_save_event(connection, event, job_id, now) for event in events)
            status = "failed" if failed else "partial" if errors else "success"
            result = JobResult(job_id, status, scanned, counts["inserted"], counts["updated"], scanned - len(events))
            connection.execute(INGESTION_JOBS.update().where(job).values(
                status=status, scanned=scanned, inserted=result.inserted, updated=result.updated,
                rejected=result.rejected, ended_at=now, error=errors or None,
            ))
            if not failed:
                connection.execute(DATA_SOURCES.update().where(_SEOUL_SOURCE).values(
                    last_success_at=func.greatest(DATA_SOURCES.c.last_success_at, now),
                ))
        return result
