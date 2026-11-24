import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import parse_qs, urlsplit

from api.ingestion.festivals.normalize import _coordinates, _event_status

SOURCE_ID = "seoul_culture"
SUPPLEMENT_FIELDS = ("official_url", "admission_fee_text")
FESTIVAL_CLASSES = frozenset({
    "축제", "축제-문화/예술", "축제-전통/역사", "축제-자연/경관", "축제-시민화합", "축제-기타",
})
PORTAL_HOST = "culture.seoul.go.kr"
DETAIL_PATH = "/culture/culture/cultureEvent/view.do"


@dataclass(frozen=True)
class SeoulFestival:
    source_item_id: str
    source_url: str
    source_image_url: str | None
    raw_checksum: str
    title: str
    start_date: date
    end_date: date
    venue_name: str | None
    latitude: float | None
    longitude: float | None
    event_status: str
    official_url: str | None
    admission_fee_text: str | None


def _text(value: object) -> str | None:
    if isinstance(value, str):
        return value.replace("\x00", "").strip() or None
    return None


def _url(value: object) -> str | None:
    url = _text(value)
    if not url or any(character.isspace() for character in url):
        return None
    try:
        parts = urlsplit(url)
        if parts.scheme in {"http", "https"} and parts.hostname and parts.username is None:
            return url
    except ValueError:
        pass
    return None


def _item_id(url: str | None) -> str | None:
    if not url:
        return None
    parts = urlsplit(url)
    if parts.netloc.lower() != PORTAL_HOST or parts.path != DETAIL_PATH:
        return None
    codes = parse_qs(parts.query).get("cultcode", [])
    if len(codes) == 1 and re.fullmatch(r"[1-9][0-9]{0,19}", codes[0]):
        return codes[0]
    return None


def _date(value: object) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?)?", value.strip(),
    ):
        return None
    try:
        return datetime.fromisoformat(value.strip()).date()
    except ValueError:
        return None


def normalized_title(value: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum())


def normalize_event(row: dict, today: date) -> tuple[SeoulFestival | None, str | None, str | None]:
    source_url = _url(row.get("HMPG_ADDR"))
    source_id = _item_id(source_url)
    start, end = _date(row.get("STRTDATE")), _date(row.get("END_DATE"))
    if start is None or end is None or end < start:
        return None, source_id, "DATE_INVALID"
    category = _text(row.get("CODENAME")) or ""
    if unicodedata.normalize("NFKC", category) not in FESTIVAL_CLASSES:
        return None, source_id, None
    title = _text(row.get("TITLE"))
    if not source_id or not source_url or not title or not normalized_title(title):
        return None, source_id, "REQUIRED_FIELD"

    lat, lng = _coordinates(row.get("LAT"), row.get("LOT")) or (None, None)
    fee = _text(row.get("USE_FEE"))
    if fee is None and _text(row.get("IS_FREE")) == "무료":
        fee = "무료"
    checksum = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    return SeoulFestival(
        source_item_id=source_id, source_url=source_url, source_image_url=_url(row.get("MAIN_IMG")),
        raw_checksum=checksum, title=title, start_date=start, end_date=end, venue_name=_text(row.get("PLACE")),
        latitude=lat, longitude=lng, event_status=_event_status(start, end, today),
        official_url=_url(row.get("ORG_LINK")), admission_fee_text=fee,
    ), source_id, None
