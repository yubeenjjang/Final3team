from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, FiniteFloat, StrictBool

from api.schemas.festivals import FestivalDetail

_MAPPING_PATH = Path(__file__).resolve().parents[1] / "data" / "seoul_crowd_mapping.json"


class _AreaMapping(BaseModel):
    area_code: str
    approved: StrictBool = False


class _FestivalMapping(BaseModel):
    festival_id: str
    region_code: str
    lat: FiniteFloat | None
    lng: FiniteFloat | None
    venue_name: str | None
    address: str | None
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


def approved_area_codes(festival: FestivalDetail) -> set[str]:
    entry = _load_mappings().get(festival.festival_id)
    if entry is None or (
        entry.region_code, entry.lat, entry.lng, entry.venue_name, entry.address
    ) != (
        festival.region_code, festival.lat, festival.lng, festival.venue_name, festival.address
    ):
        return set()
    return {area.area_code for area in entry.candidates if area.approved}
