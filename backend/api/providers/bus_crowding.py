"""서울 버스 승차 정류장의 노선·방향 대조와 차내 혼잡 조회."""

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from api.providers.festival_source import FestivalSource
from api.providers.transit_arrivals import distance_m, seoul_bus_crowding, seoul_items

MATCH_DISTANCE_M = 30
CACHE_TTL_S = 60
LOOKUP_TIMEOUT_S = 3
_BASE = "http://ws.bus.go.kr/api/rest/"
_NEARBY = _BASE + "stationinfo/getStationByPos"
_STATION = _BASE + "stationinfo/getStationByUid"
_ROUTE = _BASE + "arrive/getArrInfoByRouteAll"
_LINE_PREFIX = re.compile(r"^(?:간선|지선|광역|순환|마을|심야|공항|일반|급행|좌석|직행좌석|버스)\s*:\s*")


def stop_name(value: Any) -> str:
    return "".join(char for char in unicodedata.normalize("NFKC", _text(value)).casefold() if char.isalnum())


def route_number(value: Any) -> str:
    line = _LINE_PREFIX.sub("", unicodedata.normalize("NFKC", _text(value)))
    return "".join(line.casefold().split()).removesuffix("번")


@dataclass(frozen=True)
class BoardingStop:
    name: str
    lat: float
    lng: float
    line: str
    next_stop: str


@dataclass(frozen=True)
class SeoulStation:
    ars_id: str
    node_id: str


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _nearby_stations(rows: list[dict[str, Any]], stop: BoardingStop) -> tuple[SeoulStation, ...]:
    stations = set()
    for row in rows:
        name = row.get("stationNm") or row.get("stNm")
        ars_id = _text(row.get("arsId"))
        node_id = _text(row.get("stationId") or row.get("stId"))
        if stop_name(name) != stop.name or not re.fullmatch(r"[0-9]{5}", ars_id):
            continue
        try:
            lat, lng = float(row["gpsY"]), float(row["gpsX"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if abs(lat) <= 90 and abs(lng) <= 180 and distance_m(stop.lat, stop.lng, lat, lng) <= MATCH_DISTANCE_M:
            stations.add(SeoulStation(ars_id, node_id))
    return tuple(sorted(stations, key=lambda station: (station.ars_id, station.node_id)))


def _station_routes(rows: list[dict[str, Any]], station: SeoulStation, line: str) -> set[str]:
    return {
        route_id for row in rows
        if _text(row.get("arsId")) == station.ars_id
        and route_number(row.get("rtNm")) == line
        and re.fullmatch(r"[0-9]{9}", route_id := _text(row.get("busRouteId")))
    }


def _direction_matches(
    rows: list[dict[str, Any]], route_id: str, stations: set[SeoulStation], stop: BoardingStop,
) -> list[dict[str, Any]]:
    ordered = {}
    for row in rows:
        if _text(row.get("busRouteId")) != route_id or route_number(row.get("rtNm")) != stop.line:
            continue
        order_text = str(row["staOrd"])
        if not re.fullmatch(r"[0-9]+", order_text):
            raise ValueError
        order = int(order_text)
        if order in ordered or order < 1:
            # 동일 순번이 두 번 나오면 진행 방향을 증명할 수 없다.
            raise ValueError
        ordered[order] = row

    matches = []
    for order, row in ordered.items():
        if stop_name(row.get("stNm")) != stop.name:
            continue
        ars_id, node_id = _text(row.get("arsId")), _text(row.get("stId"))
        if not any(station.ars_id == ars_id and station.node_id in ("", node_id) for station in stations):
            continue
        following = ordered.get(order + 1, {})
        # TMAP 승차 정류장 바로 다음 정류장이 서울 노선의 증가하는 순번과 같아야 한다.
        if stop_name(following.get("stNm")) == stop.next_stop:
            matches.append(row)
    return matches


async def read_crowding(client: FestivalSource, stop: BoardingStop) -> tuple[str | None, ...]:
    async def load() -> tuple[str | None, ...]:
        nearby = await client.request(
            "seoul_bus_station", _NEARBY,
            lambda body: _nearby_stations(seoul_items(body), stop),
            params={"tmX": stop.lng, "tmY": stop.lat, "radius": MATCH_DISTANCE_M, "resultType": "json"},
        )
        route_ids_by_station = await asyncio.gather(*(
            client.request(
                "seoul_bus_station", _STATION,
                lambda body, station=station: _station_routes(seoul_items(body), station, stop.line),
                params={"arsId": station.ars_id, "resultType": "json"},
            )
            for station in nearby
        ), return_exceptions=True)
        stations_by_route: dict[str, set[SeoulStation]] = {}
        for station, route_ids in zip(nearby, route_ids_by_station, strict=True):
            if isinstance(route_ids, BaseException):
                raise route_ids
            for route_id in route_ids:
                stations_by_route.setdefault(route_id, set()).add(station)

        matches_by_route = await asyncio.gather(*(
            client.request(
                "seoul_bus_arrival", _ROUTE,
                lambda body, route_id=route_id, stations=stations: _direction_matches(
                    seoul_items(body), route_id, stations, stop,
                ),
                params={"busRouteId": route_id, "resultType": "json"},
            )
            for route_id, stations in stations_by_route.items()
        ), return_exceptions=True)
        matches = []
        for rows in matches_by_route:
            if isinstance(rows, BaseException):
                raise rows
            matches.extend(rows)
        if len(matches) != 1:
            return ()
        return tuple(seoul_bus_crowding(matches[0], order) for order in (1, 2))

    key = sha256(repr(stop).encode()).hexdigest()

    async def bounded_load() -> tuple[str | None, ...]:
        async with asyncio.timeout(LOOKUP_TIMEOUT_S):
            return await load()

    return await client.cached("route_bus_crowding", key, CACHE_TTL_S, bounded_load)
