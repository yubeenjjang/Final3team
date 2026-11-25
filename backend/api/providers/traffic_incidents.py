import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from math import cos, degrees, isfinite, radians, sin, sqrt, tan
from typing import Any, Protocol
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element

from api.providers.festival_source import FestivalSource, FestivalSourceError, public_items
from api.providers.route_base import KST, as_kst
from api.providers.transit_arrivals import distance_m
from api.schemas.festival_info import TrafficIncident, TrafficIncidentSource, TrafficIncidentType

INCIDENT_TTL_S = 60
DEFAULT_RADIUS_M = 2000
MIN_RADIUS_M = 500
MAX_RADIUS_M = 10000
MERGE_DISTANCE_M = 100
SEOUL_KEY = "SEOUL_OPEN_API_KEY"
_TOPIS = "http://openapi.seoul.go.kr:8088/{key}/xml/AccInfo"
_UTIC = "http://www.utic.go.kr/guide/imsOpenData.do"
_PAGE_SIZE = 1000
_MAX_PAGES = 40
_logger = logging.getLogger(__name__)

_POLICE_TYPES: dict[str, TrafficIncidentType] = {
    "1": "accident", "2": "construction", "3": "event", "5": "control",
}
_TOPIS_TYPES: dict[str, TrafficIncidentType] = {
    "A01": "accident", "A02": "accident", "A04": "construction",
    "사고": "accident", "공사": "construction", "행사": "event", "통제": "control",
}
_KOREAN_TIME = re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*(\d{1,2})시\s*(\d{1,2})분")


@dataclass(frozen=True)
class Incident:
    type: TrafficIncidentType
    title: str
    lat: float
    lng: float
    start_at: datetime | None
    end_at: datetime | None
    source: TrafficIncidentSource
    link_id: str | None


@dataclass(frozen=True)
class IncidentReading:
    source: TrafficIncidentSource
    observed_at: datetime
    items: list[Incident]


class UticSnapshotStore(Protocol):
    async def read(self) -> IncidentReading | None: ...

    async def save(self, reading: IncidentReading) -> None: ...


class MemoryUticSnapshotStore:
    def __init__(self) -> None:
        self._reading: IncidentReading | None = None

    async def read(self) -> IncidentReading | None:
        return self._reading

    async def save(self, reading: IncidentReading) -> None:
        self._reading = reading


def utic_enabled() -> bool:
    return os.environ.get("UTIC_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _utic_seconds(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, ""))
    except ValueError:
        return default
    return value if isfinite(value) and value > 0 else default


async def refresh_utic(client: FestivalSource, store: UticSnapshotStore) -> None:
    refresh_s = _utic_seconds("UTIC_REFRESH_S", 60)
    timeout_s = _utic_seconds("UTIC_TIMEOUT_S", 20)
    loop = asyncio.get_running_loop()
    failing = False
    while True:
        started = loop.time()
        try:
            rows = await client.request(
                "police_utic", _UTIC, key_env="UTIC_API_KEY", key_param="key", parse_xml=_utic_records,
                timeout_s=timeout_s, retry=False,
            )
            items = [item for row in rows if (item := _police_incident(row)) is not None]
            await store.save(IncidentReading("police_incident", as_kst(client.now()), items))
        except Exception:
            if not failing:
                _logger.warning("UTIC 갱신에 실패했습니다. 다음 주기에 다시 시도합니다.")
            failing = True
        else:
            failing = False
        await asyncio.sleep(max(0, refresh_s - (loop.time() - started)))


def _public_endpoint() -> str:
    endpoint = os.environ.get("POLICE_INCIDENT_API_URL", "").strip()
    try:
        parts = urlsplit(endpoint)
    except ValueError:
        raise FestivalSourceError("전국 교통 돌발 호출 주소를 확인해 주세요.", retryable=False) from None
    if (parts.scheme, parts.netloc) != ("https", "apis.data.go.kr") or (
        parts.path in {"", "/"} or parts.query or parts.fragment or "{key}" in endpoint
    ):
        raise FestivalSourceError("전국 교통 돌발 호출 주소를 확인해 주세요.", retryable=False)
    return endpoint


def _fields(element: Element) -> dict[str, str]:
    return {child.tag: (child.text or "").strip() for child in element}


def _utic_records(root: Element) -> list[dict[str, str]]:
    if root.tag != "result":
        raise ValueError
    for code in root.findall(".//resultCode"):
        if (code.text or "").strip() not in {"0", "00", "0000"}:
            # UTIC 02는 키 오류입니다. 공공데이터포털 공통 코드를 적용하지 않습니다.
            raise FestivalSourceError(retryable=False)
    if any(child.tag not in {"record", "resultCode", "resultMsg"} for child in root):
        raise ValueError
    records = [_fields(node) for node in root.findall("record")]
    return [row for row in records if "resultCode" not in row or "incidenteTypeCd" in row]


def _public_xml(root: Element) -> tuple[list[dict[str, str]], int]:
    if root.tag == "result":
        rows = _utic_records(root)
        return rows, len(rows)
    if root.tag != "response":
        raise ValueError
    header = root.find("header")
    body = root.find("body")
    if header is None:
        raise ValueError
    if body is None and (header.findtext("resultCode") or "").strip() in {"0", "00", "0000"}:
        raise ValueError
    data = _fields(body) if body is not None else {}
    data["items"] = {"item": [_fields(node) for node in root.findall("./body/items/item")]}
    return public_items({"response": {"header": _fields(header), "body": data}})


def _topis_rows(root: Element) -> tuple[list[dict[str, str]], int]:
    code = ((root.findtext("CODE") if root.tag == "RESULT" else root.findtext("./RESULT/CODE")) or "").strip()
    if code == "INFO-200":
        return [], 0
    if root.tag != "AccInfo" or code != "INFO-000":
        raise FestivalSourceError(retryable=code in {"ERROR-500", "ERROR-601"})
    return [_fields(node) for node in root.findall("row")], int(root.findtext("list_total_count", ""))


def _police_time(raw: object) -> datetime | None:
    value = raw.strip() if isinstance(raw, str) else ""
    match = _KOREAN_TIME.fullmatch(value)
    try:
        if match is not None:
            return datetime(*map(int, match.groups()), tzinfo=KST)
        return as_kst(datetime.fromisoformat(value))
    except ValueError:
        return None


def _topis_time(day: str | None, time: str | None) -> datetime | None:
    value = (time or "").strip()
    # XML 응답에 HHmm과 HHmmss가 섞여 있고 선행 0이 생략될 수 있습니다.
    if len(value) in {3, 4}:
        value = value.zfill(4) + "00"
    if len(value) == 5:
        value = value.zfill(6)
    if not day or not re.fullmatch(r"[0-9]{8}", day) or not re.fullmatch(r"[0-9]{6}", value):
        return None
    try:
        return datetime.strptime(day + value, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    except ValueError:
        return None


def _topis_coordinates(x: float, y: float) -> tuple[float, float]:
    # EPSG:5181 역 Transverse Mercator. GRS80, 원점 38°N/127°E, 가산 동쪽 200 km/북쪽 500 km.
    a = 6378137.0
    flattening = 1 / 298.257222101
    e2 = flattening * (2 - flattening)
    e4, e6 = e2 ** 2, e2 ** 3
    scale = 1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256
    origin = radians(38)
    origin_arc = a * (
        scale * origin
        - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * sin(2 * origin)
        + (15 * e4 / 256 + 45 * e6 / 1024) * sin(4 * origin)
        - 35 * e6 / 3072 * sin(6 * origin)
    )
    mu = (origin_arc + y - 500000) / (a * scale)
    n = (1 - sqrt(1 - e2)) / (1 + sqrt(1 - e2))
    foot = (
        mu + (3 * n / 2 - 27 * n ** 3 / 32) * sin(2 * mu)
        + (21 * n ** 2 / 16 - 55 * n ** 4 / 32) * sin(4 * mu)
        + 151 * n ** 3 / 96 * sin(6 * mu) + 1097 * n ** 4 / 512 * sin(8 * mu)
    )
    ep2 = e2 / (1 - e2)
    curvature = 1 - e2 * sin(foot) ** 2
    prime_vertical = a / sqrt(curvature)
    meridian = a * (1 - e2) / curvature ** 1.5
    t, c = tan(foot) ** 2, ep2 * cos(foot) ** 2
    d = (x - 200000) / prime_vertical
    lat = foot - prime_vertical * tan(foot) / meridian * (
        d ** 2 / 2 - (5 + 3 * t + 10 * c - 4 * c ** 2 - 9 * ep2) * d ** 4 / 24
        + (61 + 90 * t + 298 * c + 45 * t ** 2 - 252 * ep2 - 3 * c ** 2) * d ** 6 / 720
    )
    lng = (d - (1 + 2 * t + c) * d ** 3 / 6
           + (5 - 2 * c + 28 * t - 3 * c ** 2 + 8 * ep2 + 24 * t ** 2) * d ** 5 / 120) / cos(foot)
    return degrees(lat), 127 + degrees(lng)


def _link_id(value: object) -> str | None:
    link = str(value).strip()
    return link if link.isascii() and link.isdecimal() and link.strip("0") else None


def _police_incident(row: dict[str, Any]) -> Incident | None:
    kind = _POLICE_TYPES.get(str(row.get("incidenteTypeCd", "")).strip())
    title = str(row.get("incidentTitle") or "").strip()
    if kind is None or not title:
        return None
    try:
        lat, lng = float(row["locationDataY"]), float(row["locationDataX"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not (33 <= lat <= 39 and 124 <= lng <= 132):
        return None
    return Incident(
        kind, title, lat, lng, _police_time(row.get("startDate")), _police_time(row.get("endDate")),
        "police_incident", _link_id(row.get("linkId")),
    )


def _topis_incident(row: dict[str, str]) -> Incident | None:
    kind = _TOPIS_TYPES.get(row.get("acc_type", ""))
    title = row.get("acc_info", "")
    if kind is None or not title:
        return None
    try:
        x, y = float(row["grs80tm_x"]), float(row["grs80tm_y"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not (100000 <= x <= 300000 and 350000 <= y <= 550000):
        return None
    lat, lng = _topis_coordinates(x, y)
    return Incident(
        kind, title, lat, lng, _topis_time(row.get("occr_date"), row.get("occr_time")),
        _topis_time(row.get("exp_clr_date"), row.get("exp_clr_time")), "seoul_topis", _link_id(row.get("link_id")),
    )


async def public_incidents(client: FestivalSource) -> IncidentReading:
    endpoint = _public_endpoint()

    async def load() -> IncidentReading:
        items: list[Incident] = []
        count = 0
        for page in range(1, _MAX_PAGES + 1):
            rows, total = await client.request(
                "police_incident", endpoint, public_items, parse_xml=_public_xml,
                params={"pageNo": page, "numOfRows": _PAGE_SIZE},
            )
            count += len(rows)
            if count > total:
                raise FestivalSourceError(retryable=False)
            items.extend(item for row in rows if (item := _police_incident(row)) is not None)
            if count == total:
                return IncidentReading("police_incident", as_kst(client.now()), items)
        raise FestivalSourceError("전국 교통 돌발 페이지를 모두 확인할 수 없어요.", retryable=False)

    return await client.cached("police_incident", f"national:{endpoint}", INCIDENT_TTL_S, load)


async def topis_incidents(client: FestivalSource) -> IncidentReading:
    async def load() -> IncidentReading:
        items: list[Incident] = []
        for page in range(_MAX_PAGES):
            offset = page * _PAGE_SIZE
            rows, total = await client.request(
                "seoul_topis", f"{_TOPIS}/{offset + 1}/{offset + _PAGE_SIZE}/",
                key_env=SEOUL_KEY, parse_xml=_topis_rows,
            )
            count = offset + len(rows)
            if count > total or (count < total and len(rows) != _PAGE_SIZE):
                raise FestivalSourceError(retryable=False)
            items.extend(item for row in rows if (item := _topis_incident(row)) is not None)
            if count == total:
                return IncidentReading("seoul_topis", as_kst(client.now()), items)
        raise FestivalSourceError("서울 교통 돌발 페이지를 모두 확인할 수 없어요.", retryable=False)

    return await client.cached("seoul_topis", "SEOUL", INCIDENT_TTL_S, load)


def _same_incident(left: Incident, right: Incident) -> bool:
    if left.type != right.type or left.start_at is None or right.start_at is None:
        return False
    left_end = left.end_at or left.start_at
    right_end = right.end_at or right.start_at
    if max(left.start_at, right.start_at) > min(left_end, right_end):
        return False
    same_link = left.link_id is not None and left.link_id == right.link_id
    return same_link or " ".join(left.title.split()).casefold() == " ".join(right.title.split()).casefold()


def nearby_incidents(
    readings: list[IncidentReading], coordinates: tuple[float, float], radius_m: int,
    kind: TrafficIncidentType | None,
) -> list[TrafficIncident]:
    merged: list[tuple[float, Incident]] = []
    for reading in readings:
        nearby = [
            (distance, item) for item in reading.items if (kind is None or item.type == kind)
            and (distance := distance_m(*coordinates, item.lat, item.lng)) <= radius_m
        ]
        # 출처 한 쌍에서 사건 하나를 여러 건의 짝으로 사용하지 않습니다.
        duplicates: set[int] = set()
        additions: list[tuple[float, Incident]] = []
        for distance, item in sorted(nearby, key=lambda pair: pair[0]):
            candidates = (
                (separation, index) for index, (_, prior) in enumerate(merged)
                if index not in duplicates and _same_incident(item, prior)
                and (separation := distance_m(item.lat, item.lng, prior.lat, prior.lng)) <= MERGE_DISTANCE_M
            )
            closest = min(candidates, default=None)
            if closest is None:
                additions.append((distance, item))
            else:
                duplicates.add(closest[1])
        merged.extend(additions)
    return [
        TrafficIncident(
            type=item.type, title=item.title, lat=item.lat, lng=item.lng, distance_m=round(distance, 1),
            start_at=item.start_at, end_at=item.end_at, source=item.source,
        )
        for distance, item in sorted(merged, key=lambda pair: pair[0])
    ]
