from datetime import datetime
from typing import Any

import httpx2

from api.providers.route_base import (
    KST,
    ProviderError,
    ProviderResult,
    RouteProviderClient,
    RouteQuery,
    as_kst,
    make_candidate,
    minutes,
)

_URL = httpx2.URL(scheme="https", host="apis.openapi.sk.com", path="/transit/routes")
SERVICE_ENDED_NOTICE = "운행이 끝난 구간이 있어요"
_SERVICE_STATUS = {"0": False, "1": True}


class TmapClient(RouteProviderClient):
    provider = "tmap"
    _key_env = "TMAP_APP_KEY"
    _timeout = 5.0

    def query(self, query: RouteQuery) -> ProviderResult:
        queried_at = datetime.now(KST).isoformat()
        start_lat, start_lng = query.origin
        end_lat, end_lng = query.destination
        params: dict[str, object] = {
            "startX": start_lng,
            "startY": start_lat,
            "endX": end_lng,
            "endY": end_lat,
            "count": 3,
            "lang": 0,
            "format": "json",
        }
        if query.depart_at is not None:
            params["searchDttm"] = as_kst(query.depart_at).strftime("%Y%m%d%H%M")
        status, body = self._request_json(
            "POST",
            _URL,
            json=params,
            headers={
                "appKey": self._key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        itineraries = _itineraries(status, body)
        try:
            candidates = [
                _candidate(index, entry) for index, entry in enumerate(itineraries[:3], start=1)
            ]
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            candidates = []
        if not candidates:
            raise ProviderError("temporary", self.provider)
        available = [candidate for candidate in candidates if candidate["service_running"] is not False]
        if not available:
            raise ProviderError("service_ended", self.provider)
        notices = [SERVICE_ENDED_NOTICE] if len(available) != len(candidates) else []
        return ProviderResult(self.provider, "primary", queried_at, available, notices)


def _itineraries(status: int, body: dict[str, Any]) -> list[dict[str, Any]]:
    result = body.get("result")
    code = str(result.get("status")) if isinstance(result, dict) else ""
    if status == 400:
        kind = "region" if code == "23" else "bad_request"
        raise ProviderError(kind, "tmap")
    if code == "11":
        raise ProviderError("too_close", "tmap")
    if code in ("12", "13", "14"):
        raise ProviderError("no_result", "tmap")

    metadata = body.get("metaData")
    plan = metadata.get("plan") if isinstance(metadata, dict) else None
    itineraries = plan.get("itineraries") if isinstance(plan, dict) else None
    if not itineraries:
        raise ProviderError("no_result", "tmap")
    if not isinstance(itineraries, list):
        raise ProviderError("temporary", "tmap")
    return itineraries


def _path(leg: dict[str, Any]) -> list[list[float]]:
    linestring = (leg.get("passShape") or {}).get("linestring")
    if not linestring:
        linestring = " ".join(step.get("linestring") or "" for step in leg.get("steps") or [])
    return [
        [round(float(lat), 6), round(float(lng), 6)]
        for lng, lat in (point.split(",") for point in linestring.split())
    ]


def _stop(station: dict[str, Any]) -> dict[str, object]:
    stop = {"name": station["stationName"]}
    if station.get("stationID") is not None:
        stop["id"] = station["stationID"]
    if station.get("lat") is not None:
        stop["lat"] = float(station["lat"])
    if station.get("lon") is not None:
        stop["lng"] = float(station["lon"])
    return stop


def _leg(leg: dict[str, Any]) -> tuple[dict[str, Any], bool | None]:
    normalized = {
        "mode": {"WALK": "walk", "BUS": "bus", "SUBWAY": "subway"}[leg["mode"]],
        "duration_min": minutes(leg["sectionTime"]),
        "path": _path(leg),
    }
    running, line = _leg_service(leg)
    if line:
        normalized["line"] = line
    stations = (leg.get("passStopList") or {}).get("stations")
    if stations is not None:
        normalized["stops"] = [_stop(station) for station in stations]
    return normalized, running


def _leg_service(leg: dict[str, Any]) -> tuple[bool | None, str | None]:
    line = leg.get("route")
    primary = _SERVICE_STATUS.get(str(leg.get("service")))
    if leg["mode"] == "WALK" or primary is True:
        return True, line
    if primary is False:
        line = None

    statuses = [primary]
    for key in ("Lane", "lane"):
        lanes = leg.get(key)
        if lanes is None:
            continue
        if not isinstance(lanes, list):
            statuses.append(None)
            continue
        for lane in lanes:
            status = _SERVICE_STATUS.get(str(lane.get("service"))) if isinstance(lane, dict) else None
            statuses.append(status)
            if status is True:
                name = lane.get("route")
                if isinstance(name, str) and name.strip():
                    return True, name

    if True in statuses:
        return True, None
    if None in statuses:
        return None, line
    return False, None


def _candidate(index: int, entry: dict[str, Any]) -> dict[str, object]:
    legs = [_leg(leg) for leg in entry["legs"]]
    statuses = {running for _, running in legs}
    running = None if None in statuses else True
    if False in statuses:
        running = False
    return make_candidate(
        index,
        duration_min=minutes(entry["totalTime"]),
        distance_m=entry["totalDistance"],
        walk_m=entry["totalWalkDistance"],
        transfers=entry["transferCount"],
        fare_krw=entry["fare"]["regular"]["totalFare"],
        legs=[leg for leg, _ in legs],
        service_running=running,
        bus_crowding={"status": "unverified", "reason": "버스 혼잡 연결 전"},
    )
