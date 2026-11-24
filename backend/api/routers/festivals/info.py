from typing import Annotated

from fastapi import APIRouter, Header, Path, Query, Request

from api.providers.traffic_incidents import DEFAULT_RADIUS_M, MAX_RADIUS_M, MIN_RADIUS_M
from api.schemas.festival_info import (
    CrowdResponse, NoticeResponse, NoticeType, RealCrowdResponse, TrafficIncidentResponse,
    TrafficIncidentType, TransitMode, TransitResponse, VisitForecastResponse, WeatherResponse,
)
from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.services import mock_festival_info, real_festival_info, seoul_crowd

router = APIRouter(prefix="/festivals")
FestivalId = Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)]
Scenario = Annotated[str | None, Header(alias="X-Mock-Scenario")]


@router.get("/{festival_id}/notices")
async def get_notices(
    request: Request,
    festival_id: FestivalId,
    notice_type: Annotated[NoticeType | None, Query(alias="type")] = None,
    active_only: bool = True,
    scenario: Scenario = None,
) -> NoticeResponse:
    if real_festival_info.uses_real_info("notices"):
        result = await real_festival_info.get_service().notices(festival_id, notice_type, active_only)
    else:
        result = mock_festival_info.get_notices(festival_id, notice_type, active_only, scenario)
    request.state.result_status = result.status
    return result


@router.get("/{festival_id}/weather")
async def get_weather(request: Request, festival_id: FestivalId, scenario: Scenario = None) -> WeatherResponse:
    if real_festival_info.uses_real_info("weather"):
        result = await real_festival_info.get_service().weather(festival_id)
    else:
        result = mock_festival_info.get_weather(festival_id, scenario)
    request.state.result_status = result.status
    return result


@router.get("/{festival_id}/transit")
async def get_transit(
    request: Request, festival_id: FestivalId, mode: TransitMode = "all",
    radius_m: Annotated[int, Query(ge=100, le=1000)] = 500,
    limit: Annotated[int, Query(ge=1, le=10)] = 10,
    scenario: Scenario = None,
) -> TransitResponse:
    if real_festival_info.uses_real_info("transit"):
        result = await real_festival_info.get_service().transit(festival_id, mode, radius_m, limit)
    else:
        result = mock_festival_info.get_transit(festival_id, mode, radius_m, limit, scenario)
    request.state.result_status = result.status
    return result


@router.get("/{festival_id}/traffic-incidents")
async def get_traffic_incidents(
    request: Request, festival_id: FestivalId,
    radius_m: Annotated[int, Query(ge=MIN_RADIUS_M, le=MAX_RADIUS_M)] = DEFAULT_RADIUS_M,
    kind: Annotated[TrafficIncidentType | None, Query(alias="type")] = None,
    scenario: Scenario = None,
) -> TrafficIncidentResponse:
    if real_festival_info.uses_real_info("traffic-incidents"):
        result = await real_festival_info.get_service().traffic(festival_id, radius_m, kind)
    else:
        result = mock_festival_info.get_traffic_incidents(festival_id, radius_m, kind, scenario)
    request.state.result_status = result.status
    return result


@router.get("/{festival_id}/visit-forecast")
async def get_visit_forecast(
    request: Request, festival_id: FestivalId,
    days: Annotated[int, Query(ge=1, le=30)] = 7, scenario: Scenario = None,
) -> VisitForecastResponse:
    if real_festival_info.uses_real_info("visit-forecast"):
        result = await real_festival_info.get_service().forecast(festival_id, days)
    else:
        result = mock_festival_info.get_visit_forecast(festival_id, days, scenario)
    request.state.result_status = result.status
    return result


@router.get("/{festival_id}/crowd")
async def get_crowd(
    request: Request, festival_id: FestivalId, scenario: Scenario = None,
) -> RealCrowdResponse | CrowdResponse:
    if seoul_crowd.uses_real_crowd():
        result = await seoul_crowd.get_service().get_crowd(festival_id)
    else:
        result = mock_festival_info.get_crowd(festival_id, scenario)
    request.state.result_status = result.status
    return result
