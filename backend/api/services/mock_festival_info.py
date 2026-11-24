from datetime import datetime, timedelta

from api.errors import ApiError
from api.mocks.clock import MOCK_NOW
from api.mocks.notices import NOTICES
from api.providers.traffic_incidents import Incident, IncidentReading, nearby_incidents
from api.mocks import notices as mock_notices
from api.services.notices import active_at
from api.schemas.festival_info import (
    CongestColor,
    CongestLevel,
    Coverage,
    CrowdArea,
    CrowdForecast,
    CrowdResponse,
    InfoResponse,
    NoticeResponse,
    NoticeType,
    SourceError,
    TrafficIncidentResponse,
    TrafficIncidentType,
    TransitArrival,
    TransitMode,
    TransitResponse,
    TransitStation,
    VisitForecast,
    VisitForecastDay,
    VisitForecastResponse,
    WeatherData,
    WeatherGrid,
    WeatherResponse,
)
from api.schemas.festivals import FestivalDetail, RegionCode
from api.providers.transit_arrivals import distance_m
from api.services.festival_lookup import find_festival

_WEATHER_OBSERVED_AT = datetime.fromisoformat("2026-11-22T11:00:00+09:00")
_WEATHER: dict[RegionCode, WeatherData] = {
    "SEOUL": WeatherData(
        observed_at=_WEATHER_OBSERVED_AT,
        temperature_c=4.5,
        precipitation_mm=0.0,
        precipitation_type="none",
        grid=WeatherGrid(nx=60, ny=127),
    ),
    "BUSAN": WeatherData(
        observed_at=_WEATHER_OBSERVED_AT,
        temperature_c=9.0,
        precipitation_mm=0.0,
        precipitation_type="none",
        grid=WeatherGrid(nx=97, ny=74),
    ),
    "GANGWON": WeatherData(
        observed_at=_WEATHER_OBSERVED_AT,
        temperature_c=-3.0,
        precipitation_mm=0.5,
        precipitation_type="snow",
        grid=WeatherGrid(nx=84, ny=123),
    ),
}
_CONGEST_COLORS: dict[CongestLevel, CongestColor] = {
    "여유": "green",
    "보통": "yellow",
    "약간 붐빔": "orange",
    "붐빔": "red",
}
_CROWD_OBSERVED_AT = datetime.fromisoformat("2026-11-22T11:55:00+09:00")
_GWANGHWAMUN_LEVEL: CongestLevel = "보통"
_CROWD_AREAS = {
    "fst_000001": CrowdArea(
        area_code="POI009",
        area_name="광화문·덕수궁",
        relation_type="contains",
        congest_level=_GWANGHWAMUN_LEVEL,
        congest_color=_CONGEST_COLORS[_GWANGHWAMUN_LEVEL],
        congest_message="사람이 몰려 있을 수 있지만 크게 붐비지는 않아요.(모의)",
        population_min=48000,
        population_max=50000,
        observed_at=_CROWD_OBSERVED_AT,
        forecast=[
            CrowdForecast(
                time=MOCK_NOW + timedelta(hours=hours),
                congest_level=_GWANGHWAMUN_LEVEL,
                population_min=48000,
                population_max=50000,
            )
            for hours in range(1, 4)
        ],
    ),
}


def _find_festival(festival_id: str) -> FestivalDetail:
    festival = find_festival(festival_id)
    if festival is None:
        raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
    return festival


def _set_source_error(response: InfoResponse) -> None:
    response.status = "unavailable"
    response.error = SourceError(
        code="SOURCE_RESULT_ERROR", message="공급원 정보를 가져오지 못했어요.", retryable=True
    )


def _can_supply_data(
    response: InfoResponse,
    scenario: str | None,
    *,
    has_location: bool = True,
    unsupported_notice: str | None = None,
) -> bool:
    if not has_location:
        response.status = "unavailable"
        response.error = SourceError(
            code="FESTIVAL_LOCATION_UNKNOWN",
            message="축제 위치를 확인할 수 없어요.",
            retryable=False,
        )
        return False
    if unsupported_notice is not None:
        response.status = "unsupported"
        response.notices.append(unsupported_notice)
        return False
    if scenario == "source_error":
        _set_source_error(response)
        return False
    if scenario == "stale":
        response.status = "stale"
        response.notices.append("정보가 오래됐어요")
    elif scenario not in (None, "ok"):
        raise ApiError(422, "VALIDATION_ERROR", "X-Mock-Scenario 값을 확인해 주세요.")
    return True


def get_notices(
    festival_id: str, notice_type: NoticeType | None, active_only: bool, scenario: str | None
) -> NoticeResponse:
    festival = _find_festival(festival_id)
    response = NoticeResponse(
        festival_id=festival_id,
        coverage=Coverage(scope="national", region_code=festival.region_code, supported=True),
        source="seoul_topis" if festival.region_code == "SEOUL" else "operator",
    )
    if _can_supply_data(response, scenario):
        response.observed_at = MOCK_NOW
        fixtures = [
            notice for notice in mock_notices.NOTICES.get(festival_id, ())
            if (notice_type is None or notice.type == notice_type)
            and (not active_only or active_at(notice.effective_from, notice.effective_to, MOCK_NOW))
        ]
        managed = mock_notices.memory_store.approved(festival_id, notice_type, active_only)
        response.items = sorted(
            [*fixtures, *managed],
            key=lambda notice: notice.effective_from or datetime.min.replace(tzinfo=MOCK_NOW.tzinfo),
            reverse=True,
        )
        if not response.items:
            response.notices.append("확인할 수 있는 공지 자료가 없어요")
    return response


def get_weather(festival_id: str, scenario: str | None) -> WeatherResponse:
    festival = _find_festival(festival_id)
    response = WeatherResponse(
        festival_id=festival_id,
        coverage=Coverage(scope="national", region_code=festival.region_code, supported=True),
        source="kma",
    )
    if _can_supply_data(
        response, scenario, has_location=festival.lat is not None and festival.lng is not None
    ):
        data = _WEATHER.get(festival.region_code)
        if data is None:
            _set_source_error(response)
        else:
            response.data = data
            response.observed_at = data.observed_at
    return response


def get_traffic_incidents(
    festival_id: str, radius_m: int, kind: TrafficIncidentType | None, scenario: str | None,
) -> TrafficIncidentResponse:
    festival = _find_festival(festival_id)
    response = TrafficIncidentResponse(
        festival_id=festival_id, coverage=Coverage(scope="national", region_code=festival.region_code, supported=True),
        source="police_incident",
    )
    has_location = festival.lat is not None and festival.lng is not None
    if not _can_supply_data(response, scenario, has_location=has_location):
        return response
    response.observed_at = MOCK_NOW - timedelta(minutes=3) if scenario == "stale" else MOCK_NOW
    if festival_id == "fst_000001":
        incident = Incident(
            "control", "세종대로 임시 통제(모의)", 37.5759, 126.9771, MOCK_NOW,
            MOCK_NOW + timedelta(hours=1), "police_incident", None,
        )
        assert festival.lat is not None and festival.lng is not None
        response.items = nearby_incidents(
            [IncidentReading("police_incident", response.observed_at, [incident])],
            (festival.lat, festival.lng), radius_m, kind,
        )
    if scenario == "stale":
        response.error = SourceError(code="SOURCE_STALE", message="정보가 오래됐어요", retryable=False)
    return response


def get_crowd(festival_id: str, scenario: str | None) -> CrowdResponse:
    festival = _find_festival(festival_id)
    is_seoul = festival.region_code == "SEOUL"
    response = CrowdResponse(
        festival_id=festival_id,
        coverage=Coverage(scope="seoul_only", region_code=festival.region_code, supported=is_seoul),
        source="seoul_citydata",
    )
    area = _CROWD_AREAS.get(festival_id) if is_seoul else None
    unsupported_notice = None
    if not is_seoul:
        unsupported_notice = "이 지역은 아직 지원하지 않아요"
    elif area is None:
        unsupported_notice = "이 축제는 검증된 혼잡 구역 연결이 없어요"

    if _can_supply_data(
        response,
        scenario,
        has_location=festival.lat is not None and festival.lng is not None,
        unsupported_notice=unsupported_notice,
    ) and area is not None:
        response.areas = [area]
        response.observed_at = area.observed_at
        response.notices.extend([
            f"주변 지역 혼잡(모의 데이터) · {area.area_name}",
            "행사장 안 혼잡과 다를 수 있어요",
        ])
    return response


_MOCK_STATIONS = {
    "fst_000001": [
        ("subway", "sta_000001", "광화문", 37.5716, 126.9763, "1005"),
        ("bus", "sta_000002", "광화문광장", 37.5746, 126.9768, "703"),
    ],
    "fst_000003": [("bus", "sta_000003", "광복로", 35.1008, 129.0328, "41")],
}


def get_transit(
    festival_id: str, mode: TransitMode, radius_m: int, limit: int, scenario: str | None,
) -> TransitResponse:
    festival = _find_festival(festival_id)
    is_seoul = festival.region_code == "SEOUL"
    supported = mode != "subway" or is_seoul
    response = TransitResponse(
        festival_id=festival_id,
        coverage=Coverage(
            scope="seoul_only" if mode == "subway" else "national",
            region_code=festival.region_code, supported=supported,
        ),
        source="seoul_subway" if mode == "subway" else "seoul_bus_arrival" if is_seoul else "tago_bus",
    )
    lat, lng = festival.lat, festival.lng
    if not _can_supply_data(
        response, scenario, has_location=lat is not None and lng is not None,
        unsupported_notice=None if supported else "이 지역은 아직 지원하지 않아요",
    ) or lat is None or lng is None:
        return response
    stations = []
    for station_type, station_id, name, station_lat, station_lng, line in _MOCK_STATIONS.get(festival_id, []):
        distance = distance_m(lat, lng, station_lat, station_lng)
        if distance <= radius_m and mode in ("all", station_type):
            stations.append(TransitStation(
                type=station_type, station_id=station_id, name=name,
                lat=station_lat, lng=station_lng, distance_m=round(distance, 1),
                arrivals=[TransitArrival(line=line, eta_s=120, message="2분 후 도착")], observed_at=MOCK_NOW,
            ))
    response.stations = sorted(stations, key=lambda station: station.distance_m)[:limit]
    if response.stations:
        response.observed_at = MOCK_NOW
    else:
        response.status = "unverified"
    return response


def get_visit_forecast(festival_id: str, days: int, scenario: str | None) -> VisitForecastResponse:
    festival = _find_festival(festival_id)
    response = VisitForecastResponse(
        festival_id=festival_id,
        coverage=Coverage(scope="national", region_code=festival.region_code, supported=True),
        source="visit_forecast", forecast=VisitForecast(status="unsupported"),
    )
    if _can_supply_data(
        response, scenario,
        unsupported_notice=None if festival_id == "fst_000001" else "이 축제 장소의 예측 자료가 없어요",
    ):
        response.observed_at = MOCK_NOW
        response.forecast = VisitForecast(
            status="stale" if response.status == "stale" else "ok", attraction=festival.venue_name,
            days=[VisitForecastDay(date=MOCK_NOW.date() + timedelta(days=i), rate=45 + i) for i in range(days)],
        )
    elif response.status == "unavailable":
        response.forecast.status = "unavailable"
    return response
