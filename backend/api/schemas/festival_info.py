from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from api.schemas.common import MockResponse
from api.schemas.festivals import RegionCode

NoticeType = Literal["operation", "traffic_control", "no_stop", "bus_detour", "road_closure"]
PrecipitationType = Literal[
    "none", "rain", "rain_snow", "snow", "drizzle", "drizzle_snow", "snow_flurry"
]
CongestLevel = Literal["여유", "보통", "약간 붐빔", "붐빔"]
CongestColor = Literal["green", "yellow", "orange", "red"]


class Coverage(BaseModel):
    scope: Literal["national", "seoul_only"]
    region_code: RegionCode
    supported: bool


class SourceError(BaseModel):
    code: Literal["FESTIVAL_LOCATION_UNKNOWN", "SOURCE_RESULT_ERROR"]
    message: str
    retryable: bool


class InfoResponse(MockResponse):
    festival_id: str
    status: Literal["ok", "stale", "unavailable", "unsupported", "unverified"] = "ok"
    coverage: Coverage
    source: Literal["seoul_topis", "operator", "kma", "seoul_citydata"]
    observed_at: datetime | None = None
    notices: list[str] = Field(default_factory=list)
    error: SourceError | None = None


class Notice(BaseModel):
    notice_id: str
    type: NoticeType
    title: str
    content: str
    effective_from: datetime
    effective_to: datetime
    source: Literal["seoul_topis", "operator"]
    source_url: str | None = None
    published_at: datetime
    control_version: str | None = None


class NoticeResponse(InfoResponse):
    items: list[Notice] = Field(default_factory=list)


class WeatherGrid(BaseModel):
    nx: int
    ny: int


class WeatherForecast(BaseModel):
    status: Literal["unverified"] = "unverified"


class WeatherData(BaseModel):
    observed_at: datetime
    temperature_c: float
    precipitation_mm: float
    precipitation_type: PrecipitationType
    grid: WeatherGrid
    forecast: WeatherForecast = Field(default_factory=WeatherForecast)


class WeatherResponse(InfoResponse):
    data: WeatherData | None = None


class CrowdForecast(BaseModel):
    time: datetime
    congest_level: CongestLevel
    population_min: int
    population_max: int


class CrowdArea(BaseModel):
    area_code: str
    area_name: str
    relation_type: Literal["contains", "adjacent"]
    congest_level: CongestLevel
    congest_color: CongestColor
    congest_message: str
    population_min: int
    population_max: int
    observed_at: datetime
    forecast: list[CrowdForecast]


class CrowdResponse(InfoResponse):
    is_mock: bool = True
    areas: list[CrowdArea] = Field(default_factory=list)


class NearbyCrowdArea(BaseModel):
    area_code: str
    area_name: str
    distance_m: float
    status: Literal["ok", "stale", "unavailable"]
    data: CrowdArea | None = None
    is_estimate: bool | None = None
    error: SourceError | None = None


class RealCrowdResponse(CrowdResponse):
    is_mock: Literal[False] = False
    nearby_areas: list[NearbyCrowdArea] = Field(default_factory=list)
    is_estimate: bool | None = None
    unsupported_reason: Literal[
        "outside_seoul", "missing_coordinates", "no_approved_mapping", "no_nearby_areas",
    ] | None = None
    source_url: str
