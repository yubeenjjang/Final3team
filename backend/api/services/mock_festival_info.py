from datetime import datetime, timedelta

from api.errors import ApiError
from api.mocks.clock import MOCK_NOW
from api.mocks.notices import NOTICES
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
    WeatherData,
    WeatherGrid,
    WeatherResponse,
)
from api.schemas.festivals import FestivalDetail, RegionCode
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
        response.items = sorted(
            (
                notice
                for notice in NOTICES.get(festival_id, ())
                if (notice_type is None or notice.type == notice_type)
                and (not active_only or notice.effective_from <= MOCK_NOW <= notice.effective_to)
            ),
            key=lambda notice: notice.effective_from,
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
    return response
