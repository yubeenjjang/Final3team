from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Engine, column, func, table
from sqlalchemy.dialects.postgresql import insert
from ulid import ULID

from api.ingestion.facilities.normalize import Facility, Source, facility_id
from api.ingestion.festivals.store import DATA_SOURCES, INGESTION_JOBS

FACILITIES = table(
    "facilities", column("facility_id"), column("category"), column("name"), column("lat"),
    column("lng"), column("address"), column("region_code"), column("source_id"),
    column("source_item_id"), column("source_url"), column("ref_code"), column("collected_at"),
)
SOURCE_URL = "https://data.seoul.go.kr"
_BATCH = 1000


@dataclass(frozen=True)
class LoadResult:
    job_id: str
    scanned: int
    inserted: int
    updated: int
    rejected: int


def _register(connection, source: Source) -> None:
    connection.execute(insert(DATA_SOURCES).values(
        source_id=source.source_id, name=source.name, provider_org="서울특별시",
        scope="seoul_only", is_realtime=False, refresh_s=86400 * 30, key_site="data.seoul.go.kr",
        status="verified",
    ).on_conflict_do_nothing(index_elements=[DATA_SOURCES.c.source_id]))


def start_job(engine: Engine, source: Source, started_at: datetime) -> str:
    job_id = f"ij_{ULID()}"
    with engine.begin() as connection:
        _register(connection, source)
        connection.execute(INGESTION_JOBS.insert().values(
            job_id=job_id, source_id=source.source_id, started_at=started_at, status="running",
        ))
    return job_id


def fail_job(engine: Engine, job_id: str, code: str, now: datetime) -> None:
    with engine.begin() as connection:
        connection.execute(INGESTION_JOBS.update().where(INGESTION_JOBS.c.job_id == job_id).values(
            status="failed", ended_at=now, error=[{"stage": "facilities", "code": code}],
        ))


def finish_job(
    engine: Engine, job_id: str, source: Source, items: list[Facility], scanned: int, now: datetime,
) -> LoadResult:
    """같은 (source_id, source_item_id)는 덮어써서 재실행해도 행이 늘지 않는다."""
    inserted = updated = 0
    with engine.begin() as connection:
        for start in range(0, len(items), _BATCH):
            batch = items[start:start + _BATCH]
            statement = insert(FACILITIES).values([{
                "facility_id": facility_id(source.source_id, item.source_item_id), "category": item.category,
                "name": item.name, "lat": item.lat, "lng": item.lng, "address": item.address,
                "region_code": item.region_code, "source_id": source.source_id,
                "source_item_id": item.source_item_id, "source_url": SOURCE_URL, "ref_code": item.ref_code,
                "collected_at": now,
            } for item in batch])
            excluded = statement.excluded
            statement = statement.on_conflict_do_update(
                index_elements=[FACILITIES.c.source_id, FACILITIES.c.source_item_id],
                set_={name: getattr(excluded, name) for name in (
                    "category", "name", "lat", "lng", "address", "region_code", "source_url",
                    "ref_code", "collected_at",
                )},
            ).returning(column("xmax"))
            for (xmax,) in connection.execute(statement):
                if str(xmax) == "0":
                    inserted += 1
                else:
                    updated += 1
        # 지도에 쓰지 않는 행(의원·한강선착장·좌표 없는 주차장)과 노선별 역 행 묶음도 여기에 들어간다.
        rejected = scanned - len(items)
        connection.execute(INGESTION_JOBS.update().where(INGESTION_JOBS.c.job_id == job_id).values(
            status="success", ended_at=now, scanned=scanned,
            inserted=inserted, updated=updated, rejected=rejected,
        ))
        connection.execute(DATA_SOURCES.update().where(DATA_SOURCES.c.source_id == source.source_id).values(
            last_success_at=func.greatest(DATA_SOURCES.c.last_success_at, now),
        ))
    return LoadResult(job_id, scanned, inserted, updated, rejected)
