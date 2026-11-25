import os
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from api.errors import ApiError
from api.mocks.store import get_public_mock_festival, public_mock_festivals
from api.schemas.festivals import (
    FESTIVAL_ID_PATTERN,
    FestivalDetail,
    FestivalPage,
    FestivalQuery,
)
from api.services import festival_store

router = APIRouter()


def uses_festival_db() -> bool:
    return os.environ.get("FESTIVAL_DATA") == "db"


def _validate_period(date_from: date | None, date_to: date | None) -> None:
    if date_from is None or date_to is None:
        return
    days = (date_to - date_from).days
    if not 0 <= days <= 366:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "date_from은 date_to 이하여야 하며 두 날짜의 차이는 366일 이하여야 합니다.",
        )


def _overlaps(
    festival: FestivalDetail, date_from: date | None, date_to: date | None
) -> bool:
    if date_from is None and date_to is None:
        return True
    if festival.start_date is None or festival.end_date is None:
        return False
    return (date_from is None or festival.end_date >= date_from) and (
        date_to is None or festival.start_date <= date_to
    )


def _start_date_key(festival: FestivalDetail, descending: bool) -> tuple[bool, int]:
    if festival.start_date is None:
        return True, 0
    ordinal = festival.start_date.toordinal()
    return False, -ordinal if descending else ordinal


@router.get("/festivals")
async def list_festivals(query: Annotated[FestivalQuery, Query()]) -> FestivalPage:
    _validate_period(query.date_from, query.date_to)
    if uses_festival_db():
        return await festival_store.list_festivals(query)

    term = query.q.casefold() if query.q is not None else ""
    statuses = query.statuses
    matches = [
        festival
        for festival in public_mock_festivals()
        if (query.region == "ALL" or festival.region_code == query.region)
        and (not statuses or festival.event_status in statuses)
        and (term in festival.name.casefold() or term in (festival.venue_name or "").casefold())
        and _overlaps(festival, query.date_from, query.date_to)
    ]
    if query.sort == "name":
        matches.sort(key=lambda festival: festival.name)
    else:
        descending = query.sort == "-start_date"
        matches.sort(key=lambda festival: _start_date_key(festival, descending))

    offset = (query.page - 1) * query.page_size
    return FestivalPage(
        items=matches[offset : offset + query.page_size],
        total=len(matches),
        page=query.page,
        page_size=query.page_size,
    )


@router.get("/festivals/{festival_id}")
async def get_festival(
    festival_id: Annotated[str, Path(pattern=FESTIVAL_ID_PATTERN)],
) -> FestivalDetail:
    if uses_festival_db():
        festival = await festival_store.get_festival(festival_id)
    else:
        festival = get_public_mock_festival(festival_id)
    if festival is None:
        raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
    return festival
