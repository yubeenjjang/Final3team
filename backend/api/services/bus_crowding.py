"""선택한 귀가 후보의 버스 구간에 차내 혼잡을 표시한다."""

import asyncio
import os
from functools import lru_cache
from typing import Any

from api.errors import ApiError
from api.providers.bus_crowding import BoardingStop, read_crowding, route_number, stop_name
from api.providers.festival_source import FestivalSource, FestivalSourceError


@lru_cache(maxsize=1)
def get_client() -> FestivalSource:
    return FestivalSource()


def _boarding_stop(leg: dict[str, Any]) -> BoardingStop | None:
    stops = leg.get("stops")
    if not isinstance(stops, list) or len(stops) < 2:
        return None
    board, following = stops[:2]
    if not isinstance(board, dict) or not isinstance(following, dict):
        return None
    name = stop_name(board.get("name"))
    next_stop = stop_name(following.get("name"))
    line = route_number(leg.get("line"))
    lat, lng = board.get("lat"), board.get("lng")
    if (
        name and next_stop and name != next_stop and line
        and isinstance(lat, (float, int)) and isinstance(lng, (float, int))
    ):
        return BoardingStop(name, lat, lng, line, next_stop)
    return None


async def _leg_crowding(leg_index: int, leg: dict[str, Any], mock: bool) -> dict[str, Any]:
    stop = _boarding_stop(leg)
    if stop is None:
        return {"leg_index": leg_index, "status": "unknown"}
    # 서울 정류장 공급원 범위 밖의 좌표는 조회하지 않는다.
    if not (37.4 <= stop.lat <= 37.75 and 126.7 <= stop.lng <= 127.3):
        return {"leg_index": leg_index, "status": "unsupported"}
    try:
        levels = ("보통", None) if mock else await read_crowding(get_client(), stop)
    except (TimeoutError, FestivalSourceError):
        levels = ()
    arrivals = [
        {"arrival_order": order, "crowding": level}
        for order, level in enumerate(levels, start=1) if level is not None
    ]
    return {
        "leg_index": leg_index,
        "status": "available" if arrivals else "unknown",
        "arrivals": arrivals,
    }


async def _evidence(provider: str, candidate: dict[str, Any]) -> dict[str, Any]:
    bus_legs = [(index, leg) for index, leg in enumerate(candidate.get("legs") or []) if leg.get("mode") == "bus"]
    if provider == "kakao" or not bus_legs:
        return {"status": "unsupported"}
    mode = os.environ.get("BUS_CROWD_PROVIDER", "mock")
    if mode not in ("mock", "real") or (provider == "mock_adapter" and mode == "real"):
        return {"status": "unknown"}
    mock = mode == "mock"
    legs = await asyncio.gather(*(_leg_crowding(index, leg, mock) for index, leg in bus_legs))
    statuses = {leg["status"] for leg in legs}
    status = "available" if "available" in statuses else "unknown" if "unknown" in statuses else "unsupported"
    return {"status": status, "source": "mock" if mock else "seoul_bus_15000314", "is_mock": mock, "legs": legs}


async def selected_candidate(
    body: dict[str, Any], candidate_id: str, live_candidates: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if body["route_status"] != "ready":
        return body
    candidates = body["route_candidates"]
    selected = next((candidate for candidate in candidates if candidate["candidate_id"] == candidate_id), None)
    if selected is None:
        raise ApiError(404, "ROUTE_CANDIDATE_NOT_FOUND", "선택한 경로 후보를 찾을 수 없어요.")
    # DB의 요약에 정류장 좌표가 없으면 일치 여부를 확인할 수 없다.
    live = next(
        (candidate for candidate in live_candidates or [] if candidate["candidate_id"] == candidate_id),
        selected,
    )
    crowding = await _evidence(body["provider"], live)
    updated = {**selected, "mode_evidence": {**selected.get("mode_evidence", {}), "bus_crowding": crowding}}
    return {
        **body,
        "route_candidates": [updated if candidate is selected else candidate for candidate in candidates],
    }
