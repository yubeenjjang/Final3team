import os
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, TypeAdapter

from api.providers.festival_source import DATA_GO_KR, FestivalSource, FestivalSourceError, public_items
from api.providers.route_base import as_kst
from api.schemas.festival_info import RegionDemand, VisitForecastDay

_TOUR_API = DATA_GO_KR + "/B551011/"
_FORECAST = _TOUR_API + "TatsCnctrRateService/tatsCnctrRatedList"
_DEMAND = _TOUR_API + "AreaTarDemDsService/areaTarSjrnDsList"
_INDICATOR_CODE = "2101"
_PAGE_SIZE = 1000
_MAX_PAGES = 40
_DEFAULT_MAPPING = Path(__file__).resolve().parents[1] / "data" / "visit_forecast_mapping.json"


class AttractionMatch(BaseModel):
    attraction: str = Field(min_length=1)
    area_code: str = Field(pattern=r"^\d{2}$")
    district_code: str = Field(pattern=r"^\d{5}$")
    approved: bool = Field(default=False, strict=True)


@dataclass(frozen=True)
class TourReading:
    observed_at: datetime
    rows: list[dict[str, Any]]


@lru_cache(maxsize=4)
def _load_mappings(path: str) -> dict[str, AttractionMatch]:
    if not path:
        return {}
    try:
        return TypeAdapter(dict[str, AttractionMatch]).validate_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise FestivalSourceError("축제의 관광지 연결 설정을 확인해 주세요.", retryable=False) from None


def _normalized_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def find_attraction(festival_id: str, venue: str | None) -> AttractionMatch | None:
    match = _load_mappings(os.environ.get("VISIT_FORECAST_MAPPING_FILE", str(_DEFAULT_MAPPING))).get(festival_id)
    if match is not None and match.approved and venue and _normalized_name(venue) == _normalized_name(match.attraction):
        return match
    return None


def _in_district(row: dict[str, Any], match: AttractionMatch) -> bool:
    return str(row["areaCd"]) == match.area_code and str(row["signguCd"]) == match.district_code


def attraction_rows(reading: TourReading, match: AttractionMatch) -> TourReading:
    return TourReading(
        reading.observed_at,
        [
            row for row in reading.rows if _in_district(row, match)
            and _normalized_name(row["tAtsNm"]) == _normalized_name(match.attraction)
        ],
    )


def forecast_days(reading: TourReading) -> list[VisitForecastDay]:
    by_day: dict[date, VisitForecastDay] = {}
    for row in reading.rows:
        when = datetime.strptime(str(row["baseYmd"]), "%Y%m%d").date()
        day = VisitForecastDay(date=when, rate=float(row["cnctrRate"]))
        if when in by_day and by_day[when] != day:
            raise ValueError
        by_day[when] = day
    return [by_day[when] for when in sorted(by_day)]


def region_demand(reading: TourReading) -> RegionDemand | None:
    if not reading.rows:
        return None
    (row,) = reading.rows
    month = datetime.strptime(str(row["baseYm"]), "%Y%m").strftime("%Y-%m")
    return RegionDemand(
        indicator=row["tarSjrnDsIxNm"], value=float(row["tarSjrnDsIxVal"]),
        base_month=month, area_name=row["signguNm"],
    )


async def fetch_district_forecast(client: FestivalSource, match: AttractionMatch) -> TourReading:
    async def load() -> TourReading:
        rows: list[dict[str, Any]] = []
        for page in range(1, _MAX_PAGES + 1):
            batch, total = await client.request(
                "visit_forecast", _FORECAST, public_items, params=_params(match, page, _PAGE_SIZE),
            )
            if total < len(rows) + len(batch):
                raise FestivalSourceError(retryable=False)
            rows.extend(batch)
            if len(rows) == total:
                return TourReading(as_kst(client.now()), rows)
        raise FestivalSourceError("관광지 예측 페이지를 모두 확인할 수 없어요.", retryable=False)

    day = as_kst(client.now()).date().isoformat()
    return await client.cached("visit_forecast", f"{match.area_code}:{match.district_code}:{day}", 86_400, load)


async def fetch_region_demand(client: FestivalSource, match: AttractionMatch, month: str) -> TourReading:
    def parse(body: dict[str, Any]) -> TourReading:
        rows, total = public_items(body)
        if total > 1 or any(
            not _in_district(row, match) or str(row["baseYm"]) != month
            or str(row["tarSjrnDsIxCd"]) != _INDICATOR_CODE for row in rows
        ):
            raise ValueError
        reading = TourReading(as_kst(client.now()), rows)
        region_demand(reading)
        return reading

    day = as_kst(client.now()).date().isoformat()
    return await client.cached(
        "region_demand", f"{match.area_code}:{match.district_code}:{month}:{day}", 86_400,
        lambda: client.request(
            "region_demand", _DEMAND, parse,
            params={**_params(match, 1, 10), "baseYm": month, "tarSjrnDsIxCd": _INDICATOR_CODE},
        ),
    )


def _params(match: AttractionMatch, page: int, size: int) -> dict[str, str | int]:
    return {
        "MobileOS": "ETC", "MobileApp": "NOLDAGA", "_type": "json",
        "pageNo": page, "numOfRows": size, "areaCd": match.area_code, "signguCd": match.district_code,
    }
