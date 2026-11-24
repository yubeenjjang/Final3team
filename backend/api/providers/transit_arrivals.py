import re
from dataclasses import dataclass
from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from typing import Any
from urllib.parse import quote

from api.providers.festival_source import (
    DATA_GO_KR, FestivalSource, FestivalSourceError, item_list, public_items,
)
from api.providers.route_base import as_kst
from api.schemas.festival_info import TransitArrival

ARRIVAL_TTL_S = 30
_STATION_MATCH_M = 30
_TAGO_STOP = DATA_GO_KR + "/1613000/BusSttnInfoInqireService/getCrdntPrxmtSttnList"
_TAGO_ARRIVAL = DATA_GO_KR + "/1613000/ArvlInfoInqireService/getSttnAcctoArvlPrearngeInfoList"
_SUBWAY = "http://swopenAPI.seoul.go.kr/api/subway/{key}/json/realtimeStationArrival/0/99/"
_SEOUL_STATION = "http://ws.bus.go.kr/api/rest/stationinfo/getStationByUid"
_SEOUL_ROUTE = "http://ws.bus.go.kr/api/rest/arrive/getArrInfoByRouteAll"
_BUS_CROWDING = {"3": "여유", "4": "보통", "5": "혼잡"}


@dataclass(frozen=True)
class ArrivalReading:
    arrivals: list[TransitArrival]
    observed_at: datetime


def distance_m(lat: float, lng: float, other_lat: float, other_lng: float) -> float:
    first, second = radians(lat), radians(other_lat)
    value = sin((second - first) / 2) ** 2 + cos(first) * cos(second) * sin(radians(other_lng - lng) / 2) ** 2
    return 2 * 6_371_008.8 * asin(min(1.0, sqrt(value)))


def _name(value: str) -> str:
    return "".join(value.split()).casefold()


def _subway_name(value: str) -> str:
    name = _name(value)
    # 공식 역명 '역곡'을 유지하고 검색용 접미사만 뺀다.
    return name.removesuffix("역") if len(name) > 1 else name


def _integer(value: Any) -> int | None:
    if value is None or value == "":
        return None
    result = int(value)
    if result < 0:
        raise ValueError
    return result


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _message(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _timestamp(value: Any, now: datetime) -> datetime:
    observed = as_kst(datetime.fromisoformat(value))
    if observed > now:
        raise ValueError
    return observed


async def subway_arrivals(client: FestivalSource, name: str) -> ArrivalReading:
    station_name = _subway_name(name)

    def parse(body: dict[str, Any]) -> ArrivalReading:
        now = as_kst(client.now())
        result = body.get("errorMessage", body)
        code = result["code"]
        if code == "INFO-200":
            return ArrivalReading([], now)
        if code != "INFO-000" or str(result.get("status")) != "200":
            raise FestivalSourceError(retryable=code in {"ERROR-500", "ERROR-600", "ERROR-601"})
        rows = item_list(body.get("realtimeArrivalList"))
        matching = [row for row in rows if _subway_name(row["statnNm"]) == station_name]
        if rows and not matching:
            raise FestivalSourceError("지하철 도착 응답의 역명이 일치하지 않아요.", retryable=False)
        return ArrivalReading(
            [
                TransitArrival(
                    line=str(row["subwayId"]), direction=_string(row["updnLine"]),
                    eta_s=_integer(row["barvlDt"]), message=_message(row["arvlMsg2"]),
                )
                for row in matching
            ],
            min((_timestamp(row["recptnDt"], now) for row in matching), default=now),
        )

    return await client.cached(
        "seoul_subway", station_name, ARRIVAL_TTL_S,
        lambda: client.request(
            "seoul_subway", _SUBWAY + quote(station_name, safe=""), parse, key_env="SEOUL_SUBWAY_API_KEY",
        ),
    )


async def tago_city_code(client: FestivalSource, node_id: str, lat: float, lng: float) -> str | None:
    async def lookup() -> str | None:
        for page in range(1, 5):
            rows, total = await client.request(
                "tago_stop", _TAGO_STOP, public_items,
                params={"gpsLati": lat, "gpsLong": lng, "_type": "json", "pageNo": page, "numOfRows": 100},
            )
            matches = {str(row["citycode"]) for row in rows if row.get("nodeid") == node_id and row.get("citycode")}
            if matches:
                return next(iter(matches)) if len(matches) == 1 else None
            if page * 100 >= total:
                break
        return None

    return await client.cached("tago_stop", node_id, 600, lookup)


async def tago_arrivals(client: FestivalSource, city_code: str, node_id: str) -> ArrivalReading:
    def parse(body: dict[str, Any]) -> ArrivalReading:
        rows, _ = public_items(body)
        if any(row.get("nodeid") != node_id for row in rows):
            raise FestivalSourceError("버스 도착 응답의 정류소 ID가 일치하지 않아요.", retryable=False)
        return ArrivalReading(
            [
                TransitArrival(
                    line=str(row["routeno"]), eta_s=_integer(row["arrtime"]),
                    remaining_stops=_integer(row["arrprevstationcnt"]),
                )
                for row in rows
            ],
            as_kst(client.now()),
        )

    return await client.cached(
        "tago_bus", f"{city_code}:{node_id}", ARRIVAL_TTL_S,
        lambda: client.request(
            "tago_bus", _TAGO_ARRIVAL, parse,
            params={"cityCode": city_code, "nodeId": node_id, "_type": "json", "pageNo": 1, "numOfRows": 100},
        ),
    )


def _seoul_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    code = str(body["msgHeader"]["headerCd"])
    if code == "4":
        return []
    if code != "0":
        raise FestivalSourceError(retryable=code == "1")
    rows = item_list((body.get("msgBody") or {}).get("itemList"))
    if any(not _string(row.get("rtNm")) for row in rows):
        raise ValueError
    return rows


def matches_seoul_id(row: dict[str, Any], ars_id: str, node_id: str) -> bool:
    ars = _string(row.get("arsId"))
    node = _string(row.get("stId"))
    if ars and ars != ars_id:
        return False
    if node and node_id and node != node_id:
        return False
    return ars == ars_id or bool(node_id and node == node_id)


def match_seoul_stop(
    rows: list[dict[str, Any]], *, ars_id: str, node_id: str, name: str, lat: float, lng: float,
    line: str, direction: str | None,
) -> dict[str, Any] | None:
    same_line = [row for row in rows if _string(row.get("rtNm")) == line]
    exact = [row for row in same_line if matches_seoul_id(row, ars_id, node_id)]
    if exact:
        return exact[0] if len(exact) == 1 else None
    if not direction:
        return None
    candidates = []
    for row in same_line:
        candidate_ars = _string(row.get("arsId"))
        candidate_node = _string(row.get("stId"))
        if (
            (candidate_ars and candidate_ars.isdecimal() and candidate_ars != ars_id)
            or (candidate_node and candidate_node.isdecimal() and candidate_node != node_id)
            or _name(_string(row.get("stNm")) or "") != _name(name)
            or _string(row.get("dir")) != direction
        ):
            continue
        try:
            candidate_lat = float(row["gpsY"])
            candidate_lng = float(row["gpsX"])
        except (KeyError, TypeError, ValueError):
            continue
        if abs(candidate_lat) <= 90 and abs(candidate_lng) <= 180:
            if distance_m(lat, lng, candidate_lat, candidate_lng) <= _STATION_MATCH_M:
                candidates.append(row)
    return candidates[0] if len(candidates) == 1 else None


def _seoul_eta(message: str | None) -> int | None:
    if not message:
        return None
    message = message.strip()
    if message.startswith("곧 도착"):
        return 0
    match = re.match(r"(?:(\d+)분\s*)?(?:(\d+)초\s*)?후", message)
    if match and any(match.groups()):
        return int(match[1] or 0) * 60 + int(match[2] or 0)
    return None


def _bus_crowding(row: dict[str, Any]) -> str:
    if str(row.get("rerdie_Div1")) == "4":
        return _BUS_CROWDING.get(str(row.get("reride_Num1")), "unverified")
    return "unverified"


async def seoul_station_rows(client: FestivalSource, ars_id: str) -> tuple[list[dict[str, Any]], datetime]:
    async def load() -> tuple[list[dict[str, Any]], datetime]:
        return await client.request(
            "seoul_bus_station", _SEOUL_STATION,
            lambda body: (_seoul_items(body), as_kst(client.now())),
            params={"arsId": ars_id, "resultType": "json"},
        )

    return await client.cached("seoul_bus_station", ars_id, ARRIVAL_TTL_S, load)


async def seoul_route_rows(client: FestivalSource, route_id: str) -> list[dict[str, Any]]:
    return await client.cached(
        "seoul_bus_arrival", route_id, ARRIVAL_TTL_S,
        lambda: client.request(
            "seoul_bus_arrival", _SEOUL_ROUTE, _seoul_items,
            params={"busRouteId": route_id, "resultType": "json"},
        ),
    )


def seoul_bus_arrival(row: dict[str, Any], matched: bool) -> TransitArrival:
    message = _message(row.get("arrmsg1"))
    return TransitArrival(
        line=str(row["rtNm"]), direction=_string(row.get("dir")), eta_s=_seoul_eta(message), message=message,
        crowding=_bus_crowding(row) if matched else "unverified",
    )
