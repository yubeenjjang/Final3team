import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
REGION_CODES = {
    "11": "SEOUL",
    "26": "BUSAN",
    "27": "DAEGU",
    "28": "INCHEON",
    "29": "GWANGJU",
    "30": "DAEJEON",
    "31": "ULSAN",
    "36110": "SEJONG",
    "36": "SEJONG",
    "41": "GYEONGGI",
    "42": "GANGWON",
    "51": "GANGWON",
    "43": "CHUNGBUK",
    "44": "CHUNGNAM",
    "45": "JEONBUK",
    "52": "JEONBUK",
    "46": "JEONNAM",
    "47": "GYEONGBUK",
    "48": "GYEONGNAM",
    "50": "JEJU",
}
AREA_CODES = {
    "1": "SEOUL",
    "2": "INCHEON",
    "3": "DAEJEON",
    "4": "DAEGU",
    "5": "GWANGJU",
    "6": "BUSAN",
    "7": "ULSAN",
    "8": "SEJONG",
    "31": "GYEONGGI",
    "32": "GANGWON",
    "33": "CHUNGBUK",
    "34": "CHUNGNAM",
    "35": "GYEONGBUK",
    "36": "GYEONGNAM",
    "37": "JEONBUK",
    "38": "JEONNAM",
    "39": "JEJU",
}


@dataclass
class FestivalRecord:
    source_item_id: str
    title: str | None
    start_date: date | None
    end_date: date | None
    venue_name: str | None
    address: str | None
    latitude: float | None
    longitude: float | None
    region_code: str | None
    category: str
    summary: str | None
    admission_fee_text: str | None
    image_url: str | None
    thumbnail_url: str | None
    image_copyright_type: str | None
    official_url: str | None
    organizer: str | None
    event_status: str
    source_updated_at: datetime | None
    review_status: str
    publishable: bool
    issues: list[str]
    raw_checksum: str


def _text(value: Any) -> str | None:
    return (str(value).strip() or None) if value is not None else None


def _region(item: dict[str, Any]) -> str | None:
    code = _text(item.get("lDongRegnCd"))
    if code == "12":
        district = _text(item.get("lDongSignguCd")) or ""
        if re.fullmatch(r"[0-9]{3}", district) and 200 <= int(district) <= 399:
            return "GWANGJU"
        return "JEONNAM"
    return REGION_CODES.get(code or "") or AREA_CODES.get(_text(item.get("areacode")) or "")


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{8}", value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _dates(item: dict[str, Any], issues: list[str]) -> tuple[date | None, date | None]:
    start = _parse_date(item.get("eventstartdate"))
    end = _parse_date(item.get("eventenddate"))
    if start is None or end is None:
        issues.append("date_invalid")
    elif end < start:
        issues.append("date_invalid")
        return None, None
    return start, end


def _coordinates(
    item: dict[str, Any], issues: list[str]
) -> tuple[float | None, float | None]:
    try:
        lat, lng = float(item["mapy"]), float(item["mapx"])
        if 33 <= lat <= 39 and 124 <= lng <= 132:
            return round(lat, 6), round(lng, 6)
    except (KeyError, TypeError, ValueError, OverflowError):
        pass
    issues.append("coords_out_of_range")
    return None, None


def _images(
    item: dict[str, Any], issues: list[str]
) -> tuple[str | None, str | None, str | None]:
    image = _text(item.get("firstimage"))
    if image is None:
        return None, None, None
    copyright_type = _text(item.get("cpyrhtDivCd"))
    if copyright_type not in {"Type1", "Type3"}:
        issues.append("image_copyright_unknown")
        return None, None, None
    return image, _text(item.get("firstimage2")), copyright_type


def _event_status(start: date | None, end: date | None, today: date) -> str:
    if start is None or end is None:
        return "needs_review"
    if today < start:
        return "upcoming"
    if today > end:
        return "ended"
    return "ongoing"


def _updated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{14}", value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    except ValueError:
        return None


class _DetailHTML(HTMLParser):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.href: str | None = None
        self.feed(value)
        self.close()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br":
            self.parts.append("\n")
        if self.href is None:
            for name, value in attrs:
                if name == "href":
                    self.href = value or ""
                    break

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _detail_text(value: Any) -> str | None:
    content = _text(value)
    return _text("".join(_DetailHTML(content).parts)) if content else None


def _summary(value: Any) -> str | None:
    content = _detail_text(value)
    if content is None:
        return None
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n[^\S\n]*\n(?:[^\S\n]*\n)*", "\n\n", content)[:2000].rstrip()


def _official_url(value: str | None) -> str | None:
    if value is None:
        return None
    if "<" in value:
        value = _text(_DetailHTML(value).href) or ""
    scheme, separator, _ = value.partition("://")
    return value if separator and scheme.lower() in {"https", "http"} else None


def normalize_festival(
    item: dict[str, Any],
    common: dict[str, Any] | None = None,
    intro: dict[str, Any] | None = None,
    *,
    today: date,
    details_requested: bool = True,
) -> FestivalRecord:
    issues: list[str] = []
    title = _text(item.get("title"))
    region = _region(item)
    if title is None:
        issues.append("title_missing")
    if region is None:
        issues.append("region_unknown")
    start, end = _dates(item, issues)
    lat, lng = _coordinates(item, issues)
    image, thumbnail, copyright_type = _images(item, issues)

    publishable = all(value is not None for value in (title, start, end, lat, lng, region))
    if details_requested and (not common or not intro):
        issues.append("detail_missing")
    raw_json = json.dumps([item, common, intro], sort_keys=True, ensure_ascii=False)
    common = common or {}
    intro = intro or {}
    address_parts = [_text(item.get(field)) for field in ("addr1", "addr2")]

    return FestivalRecord(
        source_item_id=_text(item.get("contentid")) or "",
        title=title,
        start_date=start,
        end_date=end,
        venue_name=_text(intro.get("eventplace")),
        address=" ".join(part for part in address_parts if part) or None,
        latitude=lat,
        longitude=lng,
        region_code=region,
        category="festival",
        summary=_summary(common.get("overview")),
        admission_fee_text=_detail_text(intro.get("usetimefestival")),
        image_url=image,
        thumbnail_url=thumbnail,
        image_copyright_type=copyright_type,
        official_url=_official_url(_text(intro.get("eventhomepage")) or _text(common.get("homepage"))),
        organizer=_text(intro.get("sponsor1")),
        event_status=_event_status(start, end, today),
        source_updated_at=_updated_at(item.get("modifiedtime")),
        review_status="approved" if publishable else "pending",
        publishable=publishable,
        issues=issues,
        raw_checksum=hashlib.sha256(raw_json.encode()).hexdigest(),
    )
