import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from hashlib import sha256
from math import cos, radians
from typing import Literal

from sqlalchemy import Engine, text

from api.ingestion.db import create_ingestion_engine
from api.providers.visit_forecast import TourReading

from api.schemas.festival_info import Notice, NoticeType, TransitMode
from api.services.festival_store import get_festival_engine


@dataclass(frozen=True)
class FacilityStation:
    type: Literal["subway", "bus"]
    station_id: str
    name: str
    lat: float
    lng: float
    region_code: str | None
    source_id: str
    source_item_id: str
    ref_code: str | None


def approved_notices(
    festival_id: str, notice_type: NoticeType | None, active_only: bool, now: datetime,
) -> list[Notice]:
    query = text("""
        SELECT notice_id, type, title, content, effective_from, effective_to,
               source_id AS source, source_url, published_at, control_version
          FROM official_notices
         WHERE festival_id = :festival_id AND approval_status = 'approved'
           AND (:all_types OR type = :notice_type)
           AND (:all_dates OR ((effective_from IS NULL OR effective_from <= :now)
                          AND (effective_to IS NULL OR effective_to >= :now)))
         ORDER BY effective_from DESC NULLS LAST, notice_id
    """)
    with get_festival_engine().connect() as connection:
        rows = connection.execute(query, {
            "festival_id": festival_id, "all_types": notice_type is None,
            "notice_type": notice_type, "all_dates": not active_only, "now": now,
        }).mappings()
        return [Notice.model_validate(row) for row in rows]


def nearby_facilities(lat: float, lng: float, radius_m: int, mode: TransitMode) -> list[FacilityStation]:
    query = text("""
        SELECT CASE category WHEN 'subway_station' THEN 'subway' ELSE 'bus' END AS type,
               facility_id AS station_id, name, lat, lng, region_code, source_id, source_item_id, ref_code
          FROM facilities
         WHERE lat BETWEEN :south AND :north AND lng BETWEEN :west AND :east
           AND ((category = 'bus_stop' AND :bus) OR (category = 'subway_station' AND :subway))
    """)
    lat_delta = radius_m / 110_000
    lng_delta = lat_delta / cos(radians(lat))
    with get_festival_engine().connect() as connection:
        rows = connection.execute(query, {
            "south": lat - lat_delta, "north": lat + lat_delta,
            "west": lng - lng_delta, "east": lng + lng_delta,
            "bus": mode != "subway", "subway": mode != "bus",
        }).mappings()
        return [
            FacilityStation(
                type=row.type, station_id=row.station_id, name=row.name, lat=float(row.lat),
                lng=float(row.lng), region_code=row.region_code, source_id=row.source_id,
                source_item_id=row.source_item_id, ref_code=row.ref_code,
            )
            for row in rows
        ]


def read_tour_snapshot(source: str, target: str, since: datetime, now: datetime) -> TourReading | None:
    query = text("""
        SELECT observed_at, payload
          FROM realtime_snapshots
         WHERE source_id = :source AND data_type = :source AND target_id = :target
           AND sample_kind = 'original' AND observed_at >= :since AND observed_at <= :now
         ORDER BY observed_at DESC LIMIT 1
    """)
    with _snapshot_engine().connect() as connection:
        row = connection.execute(query, {"source": source, "target": target, "since": since, "now": now}).first()
    if row is None:
        return None
    return TourReading(row.observed_at, row.payload["items"])


def save_tour_snapshot(source: str, target: str, region: str, reading: TourReading) -> None:
    since = reading.observed_at.replace(hour=0, minute=0, second=0, microsecond=0)
    payload = json.dumps({"items": reading.rows}, ensure_ascii=False, sort_keys=True)
    parameters = {
        "source": source, "target": target, "region": region, "observed_at": reading.observed_at,
        "since": since, "payload": payload, "digest": sha256(payload.encode()).hexdigest(),
        "name": "관광지 집중률 방문자 추이 예측" if source == "visit_forecast" else "지역별 관광 수요 강도",
        "target_type": "attraction" if source == "visit_forecast" else "region",
    }
    with _snapshot_engine().begin() as connection:
        connection.execute(text("""
            INSERT INTO data_sources (source_id, name, provider_org, scope, is_realtime, refresh_s)
            VALUES (:source, :name, '한국관광공사', 'national', false, 86400)
            ON CONFLICT (source_id) DO NOTHING
        """), parameters)
        connection.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:source), hashtext(:target))"), parameters,
        )
        connection.execute(text("""
            INSERT INTO realtime_snapshots (
                source_id, data_type, target_type, target_id, region_code, observed_at,
                payload, payload_hash, source_result_code, sample_kind
            )
            SELECT :source, :source, :target_type, :target, :region, :observed_at,
                   CAST(:payload AS jsonb), :digest, '0000', 'original'
             WHERE NOT EXISTS (
                SELECT 1 FROM realtime_snapshots
                 WHERE source_id = :source AND data_type = :source AND target_id = :target
                   AND sample_kind = 'original' AND observed_at >= :since
             )
        """), parameters)


@lru_cache(maxsize=1)
def _snapshot_engine() -> Engine:
    return create_ingestion_engine(pool_pre_ping=True)
