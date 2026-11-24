from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

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
    code: Literal[
        "FESTIVAL_LOCATION_UNKNOWN", "REGION_UNSUPPORTED", "SOURCE_HTTP_ERROR",
        "SOURCE_RESULT_ERROR", "SOURCE_STALE",
    ]
    message: str
    retryable: bool


InfoStatus = Literal["ok", "stale", "unavailable", "unsupported", "unverified"]
TransitMode = Literal["all", "subway", "bus"]
TrafficIncidentType = Literal["accident", "construction", "event", "control"]
TrafficIncidentSource = Literal["police_incident", "seoul_topis"]


class InfoResponse(BaseModel):
    is_mock: bool = True
    festival_id: str
    status: InfoStatus = "ok"
    coverage: Coverage
    source: str
    observed_at: datetime | None = None
    notices: list[str] = Field(default_factory=list)
    error: SourceError | None = None


class Notice(BaseModel):
    notice_id: str
    type: NoticeType
    title: str
    content: str | None
    effective_from: datetime | None
    effective_to: datetime | None
    source: str | None
    source_url: str | None = None
    published_at: datetime | None
    control_version: str | None = None


class NoticeResponse(InfoResponse):
    items: list[Notice] = Field(default_factory=list)


class WeatherGrid(BaseModel):
    nx: int
    ny: int


class WeatherForecast(BaseModel):
    status: Literal["unverified"] = "unverified"


class WeatherForecastItem(BaseModel):
    forecast_at: datetime
    temperature_c: float
    precipitation_mm: float | None
    precipitation_type: PrecipitationType


class RealWeatherForecast(BaseModel):
    status: Literal["ok", "stale"]
    issued_at: datetime
    items: list[WeatherForecastItem]


class FailedWeatherForecast(BaseModel):
    status: Literal["unavailable"] = "unavailable"
    error: SourceError


class WeatherData(BaseModel):
    observed_at: datetime
    temperature_c: float
    precipitation_mm: float
    precipitation_type: PrecipitationType
    grid: WeatherGrid
    forecast: WeatherForecast | RealWeatherForecast | FailedWeatherForecast = Field(default_factory=WeatherForecast)


class WeatherResponse(InfoResponse):
    data: WeatherData | None = None


class TransitArrival(BaseModel):
    line: str
    direction: str | None = None
    eta_s: int | None = None
    message: str | None = None
    remaining_stops: int | None = None
    crowding: Literal["여유", "보통", "혼잡", "unverified"] | None = None


class TransitStation(BaseModel):
    type: Literal["subway", "bus"]
    station_id: str
    name: str
    lat: float
    lng: float
    distance_m: float
    status: InfoStatus = "ok"
    arrivals: list[TransitArrival] = Field(default_factory=list)
    observed_at: datetime | None = None


class TransitResponse(InfoResponse):
    stations: list[TransitStation] = Field(default_factory=list)


class TrafficIncident(BaseModel):
    type: TrafficIncidentType
    title: str
    lat: float
    lng: float
    distance_m: float
    start_at: datetime | None
    end_at: datetime | None
    source: TrafficIncidentSource


class TrafficIncidentResponse(InfoResponse):
    items: list[TrafficIncident] = Field(default_factory=list)


class VisitForecastDay(BaseModel):
    date: date
    rate: float = Field(ge=0, le=100)


class VisitForecast(BaseModel):
    status: Literal["ok", "stale", "unavailable", "unsupported"]
    attraction: str | None = None
    days: list[VisitForecastDay] = Field(default_factory=list)


class RegionDemand(BaseModel):
    indicator: str
    value: float = Field(allow_inf_nan=False)
    base_month: str
    area_name: str


class VisitForecastResponse(InfoResponse):
    forecast: VisitForecast
    region_demand: RegionDemand | None = None


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
