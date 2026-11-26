import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from api.providers.transit_arrivals import distance_m

SEOUL = "SEOUL"
# 같은 이름의 역이라도 이 거리보다 멀면 다른 역(예: 경의중앙선 양평과 5호선 양평)으로 본다.
_SAME_STATION_M = 1000
_HOSPITAL_DIVISIONS = {"A", "B"}  # 종합병원·병원. 의원·치과·한의원은 지도에 너무 많아 제외한다.


@dataclass(frozen=True)
class Facility:
    category: str
    name: str
    lat: float
    lng: float
    address: str | None
    region_code: str | None
    source_item_id: str
    ref_code: str | None = None


@dataclass(frozen=True)
class Source:
    source_id: str
    service: str
    name: str
    normalize: Callable[[list[dict]], list[Facility]]


def _text(value: object) -> str | None:
    if isinstance(value, str):
        return value.replace("\x00", "").strip() or None
    if isinstance(value, int | float) and not isinstance(value, bool):
        return str(value)
    return None


def _coord(lat: object, lng: object) -> tuple[float, float] | None:
    try:
        y, x = float(lat), float(lng)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not (33 <= y <= 39 and 124 <= x <= 132):
        return None
    return round(y, 6), round(x, 6)


def facility_id(source_id: str, source_item_id: str) -> str:
    digest = hashlib.sha256(f"{source_id}\x1f{source_item_id}".encode()).hexdigest()[:24]
    return f"fac_{digest}"


def bus_stops(rows: list[dict]) -> list[Facility]:
    # busStopLocationXyInfo: STOPS_NO = 정류소 ID(9자리, 서울 버스 API stId), NODE_ID = ARS 번호(5자리).
    items = []
    for row in rows:
        node_id, ars_id, name = _text(row.get("STOPS_NO")), _text(row.get("NODE_ID")), _text(row.get("STOPS_NM"))
        point = _coord(row.get("YCRD"), row.get("XCRD"))
        if _text(row.get("STOPS_TYPE")) == "한강선착장" or not (node_id and name and point):
            continue
        ref = ars_id.zfill(5) if ars_id and ars_id.isdecimal() and len(ars_id) <= 5 else None
        items.append(Facility("bus_stop", name, *point, None, SEOUL, node_id, ref))
    return items


def subway_stations(rows: list[dict]) -> list[Facility]:
    # 노선별 행을 역 하나로 묶는다. 서울 지하철 도착 API는 역 이름으로 모든 노선을 돌려준다.
    groups: dict[str, list[list[tuple[str, float, float]]]] = {}
    for row in sorted(rows, key=lambda r: str(r.get("BLDN_ID"))):
        code, name = _text(row.get("BLDN_ID")), _text(row.get("BLDN_NM"))
        point = _coord(row.get("LAT"), row.get("LOT"))
        if not (code and name and point):
            continue
        clusters = groups.setdefault(name, [])
        for cluster in clusters:
            if distance_m(cluster[0][1], cluster[0][2], *point) <= _SAME_STATION_M:
                cluster.append((code, *point))
                break
        else:
            clusters.append([(code, *point)])
    items = []
    for name, clusters in groups.items():
        for cluster in clusters:
            codes = [code for code, _, _ in cluster]
            lat = round(sum(p[1] for p in cluster) / len(cluster), 6)
            lng = round(sum(p[2] for p in cluster) / len(cluster), 6)
            item_id = name if len(clusters) == 1 else f"{name}#{codes[0]}"
            # 도착 API는 괄호 속 부역명 없이 역 이름만 받는다(예: 서울대입구(관악구청) → 서울대입구).
            plain = re.sub(r"\s*\([^)]*\)", "", name).strip() or name
            display = plain if plain.endswith("역") else f"{plain}역"
            # 지역은 비워 둔다. A26은 비어 있으면 축제 지역으로 서울 지하철 지원 여부를 판단한다.
            items.append(Facility("subway_station", display, lat, lng, None, None, item_id, codes[0]))
    return items


def bike_stations(rows: list[dict]) -> list[Facility]:
    items = []
    for row in rows:
        code = _text(row.get("RNTLS_ID"))
        point = _coord(row.get("LAT"), row.get("LOT"))
        if not (code and point):
            continue
        detail, address = _text(row.get("ADDR2")), _text(row.get("ADDR1"))
        label = detail if detail and not detail.isdecimal() else address or code
        items.append(Facility("bike_zone", f"따릉이 {label}", *point, address, SEOUL, code, code))
    return items


def toilets(rows: list[dict]) -> list[Facility]:
    items = []
    for row in rows:
        item_id, name = _text(row.get("OBJECTID")), _text(row.get("CONTS_NAME"))
        point = _coord(row.get("COORD_Y"), row.get("COORD_X"))
        if not (item_id and name and point):
            continue
        item_id = item_id.removesuffix(".0")
        address = _text(row.get("ADDR_NEW")) or _text(row.get("ADDR_OLD"))
        items.append(Facility("toilet", name, *point, address, SEOUL, item_id))
    return items


def parking_lots(rows: list[dict]) -> list[Facility]:
    # GetParkInfo는 같은 주차장이 여러 행(요금 구분)으로 온다. 좌표 0인 행은 위치가 없는 것이다.
    seen: dict[str, Facility] = {}
    for row in rows:
        code, name = _text(row.get("PKLT_CD")), _text(row.get("PKLT_NM"))
        point = _coord(row.get("LAT"), row.get("LOT"))
        if code and name and point and code not in seen:
            seen[code] = Facility("parking", name, *point, _text(row.get("ADDR")), SEOUL, code)
    return list(seen.values())


def hospitals(rows: list[dict]) -> list[Facility]:
    items = []
    for row in rows:
        hpid, name = _text(row.get("HPID")), _text(row.get("DUTYNAME"))
        point = _coord(row.get("WGS84LAT"), row.get("WGS84LON"))
        if not (hpid and name and point):
            continue
        address = _text(row.get("DUTYADDR"))
        if _text(row.get("DUTYDIV")) in _HOSPITAL_DIVISIONS:
            items.append(Facility("hospital", name, *point, address, SEOUL, hpid))
        if _text(row.get("DUTYERYN")) == "1":  # 응급실 운영
            items.append(Facility("emergency", name, *point, address, SEOUL, f"{hpid}:emergency"))
    return items


SOURCES: dict[str, Source] = {source.source_id: source for source in (
    Source("seoul_bus_stop", "busStopLocationXyInfo", "서울시 버스정류소 위치정보", bus_stops),
    Source("seoul_subway_station", "subwayStationMaster", "서울시 역사마스터 정보", subway_stations),
    Source("seoul_bike_station", "bikeStationMaster", "서울시 공공자전거 대여소 정보", bike_stations),
    Source("seoul_public_toilet", "mgisToiletPoi", "서울시 공중화장실 위치정보", toilets),
    Source("seoul_public_parking", "GetParkInfo", "서울시 공영주차장 안내 정보", parking_lots),
    Source("seoul_hospital", "TbHospitalInfo", "서울시 병의원 위치 정보", hospitals),
)}


def unique(items: Iterable[Facility]) -> tuple[list[Facility], int]:
    """같은 원본 ID가 두 번 오면 처음 것만 쓴다(재실행 멱등성)."""
    seen: dict[str, Facility] = {}
    duplicates = 0
    for item in items:
        if item.source_item_id in seen:
            duplicates += 1
        else:
            seen[item.source_item_id] = item
    return list(seen.values()), duplicates
