from typing import Annotated

from fastapi import APIRouter, Header, Path, Query

from api.schemas.festival_info import CrowdResponse, NoticeResponse, NoticeType, WeatherResponse
from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.services import mock_festival_info

router = APIRouter(prefix="/festivals")
FestivalId = Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)]
Scenario = Annotated[str | None, Header(alias="X-Mock-Scenario")]


@router.get("/{festival_id}/notices")
async def get_notices(
    festival_id: FestivalId,
    notice_type: Annotated[NoticeType | None, Query(alias="type")] = None,
    active_only: bool = True,
    scenario: Scenario = None,
) -> NoticeResponse:
    return mock_festival_info.get_notices(festival_id, notice_type, active_only, scenario)


@router.get("/{festival_id}/weather")
async def get_weather(festival_id: FestivalId, scenario: Scenario = None) -> WeatherResponse:
    return mock_festival_info.get_weather(festival_id, scenario)


@router.get("/{festival_id}/crowd")
async def get_crowd(festival_id: FestivalId, scenario: Scenario = None) -> CrowdResponse:
    return mock_festival_info.get_crowd(festival_id, scenario)
