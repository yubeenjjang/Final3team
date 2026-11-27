from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, FiniteFloat, StrictBool

from api.schemas.festivals import FestivalDetail
from api.services.seoul_areas import point_distance_m

_MAPPING_PATH = Path(__file__).resolve().parents[1] / "data" / "seoul_crowd_mapping.json"
MAX_COORDINATE_DRIFT_M = 100.0


class _AreaMapping(BaseModel):
    area_code: str
    approved: StrictBool = False
    approved_at: str | None = None


class _FestivalMapping(BaseModel):
    festival_id: str
    region_code: str
    lat: FiniteFloat | None
    lng: FiniteFloat | None
    venue_name: str | None
    address: str | None
    decision: str | None = None
    reasons: list[str] = []
    candidates: list[_AreaMapping]


class _MappingDocument(BaseModel):
    schema_version: Literal[1]
    festivals: list[_FestivalMapping]


@lru_cache(maxsize=1)
def _load_mappings() -> dict[str, _FestivalMapping]:
    try:
        data = _MappingDocument.model_validate_json(_MAPPING_PATH.read_bytes())
    except (OSError, ValueError):
        return {}
    by_id = {entry.festival_id: entry for entry in data.festivals}
    return by_id if len(by_id) == len(data.festivals) else {}


def _same_location(entry: _FestivalMapping, festival: FestivalDetail) -> bool:
    if entry.region_code != festival.region_code:
        return False
    if entry.lat is None or entry.lng is None or festival.lat is None or festival.lng is None:
        return False
    if not (isfinite(festival.lat) and isfinite(festival.lng)):
        return False
    return point_distance_m(entry.lat, entry.lng, festival.lat, festival.lng) <= MAX_COORDINATE_DRIFT_M


# 사람이 직접 봐야 하는 매핑 사유: 점 하나로 자동 판정하면 틀릴 수 있다.
HUMAN_REVIEW_REASONS = frozenset({"multiple_sites_or_route", "venue_to_confirm", "missing_venue_name"})


def needs_human_review(festival: FestivalDetail) -> bool:
    """자동 승인하면 안 되는 축제인지 판단한다.

    - 여러 장소·긴 경로이거나 장소 확인이 필요한 축제(점 하나로 구역을 고를 수 없음)
    - 사람이 승인했다가 취소한 후보가 있는 축제(사람 결정이 자동 판정보다 우선)
    """
    entry = _load_mappings().get(festival.festival_id)
    if entry is None or not _same_location(entry, festival):
        return False
    if HUMAN_REVIEW_REASONS.intersection(entry.reasons):
        return True
    return any(area.approved_at and not area.approved for area in entry.candidates)


def approved_area_codes(festival: FestivalDetail) -> set[str]:
    entry = _load_mappings().get(festival.festival_id)
    if entry is None or not _same_location(entry, festival):
        return set()
    return {area.area_code for area in entry.candidates if area.approved}
