import hashlib
import json
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from api.ingestion.festivals.normalize import FestivalRecord, normalize_festival

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 16)


def fixture_items(name: str) -> list[dict[str, Any]]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return payload["response"]["body"]["items"]["item"]


@pytest.fixture
def listing() -> dict[str, Any]:
    return fixture_items("search_page1.json")[0]


def test_I3_record_fields(listing: dict[str, Any]) -> None:
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert {field.name for field in fields(FestivalRecord)} == {
        "source_item_id", "title", "start_date", "end_date", "venue_name", "address",
        "latitude", "longitude", "region_code", "category", "source_class_level1",
        "source_class_level2", "source_class_code", "summary", "admission_fee_text",
        "image_url", "thumbnail_url", "image_copyright_type", "official_url", "organizer",
        "event_status", "source_updated_at", "review_status", "publishable", "issues", "raw_checksum",
    }
    assert record.source_item_id == "3379778"
    assert record.title == "가락 옥토버페스트"
    assert isinstance(record.publishable, bool)
    assert isinstance(record.issues, list)


@pytest.mark.parametrize(
    ("region", "district", "area", "expected"),
    [
        ("11", "", "", "SEOUL"),
        ("36110", "", "", "SEJONG"),
        ("36", "", "", "SEJONG"),
        ("51", "", "", "GANGWON"),
        ("52", "", "", "JEONBUK"),
        ("12", "210", "", "GWANGJU"),
        ("12", "130", "", "JEONNAM"),
        ("12", "200", "", "GWANGJU"),
        ("12", "399", "", "GWANGJU"),
        ("12", "400", "", "JEONNAM"),
        ("99", "", "6", "BUSAN"),
        ("99", "", "", None),
    ],
)
def test_I4_region_codes(
    listing: dict[str, Any], region: str, district: str, area: str, expected: str | None
) -> None:
    listing.update(lDongRegnCd=region, lDongSignguCd=district, areacode=area)
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert record.region_code == expected
    assert record.issues == (["region_unknown"] if expected is None else [])


@pytest.mark.parametrize(
    ("start", "end", "expected_start", "expected_end"),
    [
        ("20261016", "20261018", date(2026, 10, 16), date(2026, 10, 18)),
        ("2026-10-16", "20261018", None, date(2026, 10, 18)),
        ("2026106", "20261018", None, date(2026, 10, 18)),
        ("20260229", "20261018", None, date(2026, 10, 18)),
        ("20261016", "20261015", None, None),
    ],
)
def test_I5_date_values(
    listing: dict[str, Any], start: str, end: str,
    expected_start: date | None, expected_end: date | None,
) -> None:
    listing.update(eventstartdate=start, eventenddate=end)
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert (record.start_date, record.end_date) == (expected_start, expected_end)
    assert record.issues == ([] if expected_start and expected_end else ["date_invalid"])


def test_I5_coordinates_round_and_reject_real_outlier(listing: dict[str, Any]) -> None:
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert (record.latitude, record.longitude) == (37.496025, 127.110753)
    outlier = next(
        item for item in fixture_items("search_page1.json") if item["contentid"] == "2865122"
    )
    record = normalize_festival(outlier, today=TODAY, details_requested=False)
    assert (record.latitude, record.longitude) == (None, None)
    assert record.issues == ["coords_out_of_range"]


@pytest.mark.parametrize(
    ("lat", "lng", "valid"), [("33", "124", True), ("39", "132", True), ("NaN", "", False)]
)
def test_I5_coordinate_boundaries(
    listing: dict[str, Any], lat: str, lng: str, valid: bool
) -> None:
    listing.update(mapy=lat, mapx=lng)
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert (record.latitude, record.longitude) == ((float(lat), float(lng)) if valid else (None, None))
    assert ("coords_out_of_range" in record.issues) is not valid


@pytest.mark.parametrize(
    ("image", "thumbnail", "copyright_type", "expected", "issue"),
    [
        ("image", "thumb", "Type3", ("image", "thumb", "Type3"), []),
        ("image", "", "Type1", ("image", None, "Type1"), []),
        ("image", "thumb", "Type2", (None, None, None), ["image_copyright_unknown"]),
        ("image", "thumb", "", (None, None, None), ["image_copyright_unknown"]),
        ("", "thumb", "Type3", (None, None, None), []),
    ],
)
def test_I5_image_copyright(
    listing: dict[str, Any], image: str, thumbnail: str, copyright_type: str,
    expected: tuple[str | None, str | None, str | None], issue: list[str],
) -> None:
    listing.update(firstimage=image, firstimage2=thumbnail, cpyrhtDivCd=copyright_type)
    record = normalize_festival(listing, today=TODAY, details_requested=False)
    assert (record.image_url, record.thumbnail_url, record.image_copyright_type) == expected
    assert record.issues == issue
    assert record.publishable


@pytest.mark.parametrize(
    ("day", "expected"), [(15, "upcoming"), (16, "ongoing"), (18, "ongoing"), (19, "ended")]
)
def test_I5_event_status(listing: dict[str, Any], day: int, expected: str) -> None:
    record = normalize_festival(listing, today=date(2026, 10, day), details_requested=False)
    assert record.event_status == expected


def test_I5_category_timestamp_and_stable_checksum(listing: dict[str, Any]) -> None:
    common = fixture_items("common_3379778.json")[0]
    intro = fixture_items("intro_3379778.json")[0]
    record = normalize_festival(listing, common, intro, today=TODAY)
    assert record.category == "festival"
    assert record.source_updated_at == datetime(2026, 10, 6, 9, 15, 2, tzinfo=ZoneInfo("Asia/Seoul"))
    assert record.source_updated_at.isoformat().endswith("+09:00")
    sorted_json = json.dumps([listing, common, intro], sort_keys=True, ensure_ascii=False)
    assert record.raw_checksum == hashlib.sha256(sorted_json.encode()).hexdigest()
    reordered = dict(reversed(listing.items()))
    assert normalize_festival(reordered, common, intro, today=TODAY).raw_checksum == record.raw_checksum
    for items in (
        (listing | {"raw_field": 1}, common, intro),
        (listing, common | {"raw_field": 1}, intro),
        (listing, common, intro | {"raw_field": 1}),
    ):
        assert normalize_festival(*items, today=TODAY).raw_checksum != record.raw_checksum


@pytest.mark.parametrize(
    ("level2", "level3", "category"),
    [
        ("EV01", "EV010600", "festival"),
        ("EV02", "EV020100", "performance"),
        ("EV03", "EV030100", "event"),
        ("EV99", "EV990100", "unknown"),
        ("", "", "unknown"),
        (None, None, "unknown"),
    ],
)
def test_I18_classification_uses_listing_codes(
    listing: dict[str, Any], level2: str | None, level3: str | None, category: str,
) -> None:
    listing.pop("lclsSystm2")
    listing.pop("lclsSystm3")
    listing["lclsSystm1"] = " EV "
    if level2 is not None:
        listing.update(lclsSystm2=f" {level2} ", lclsSystm3=f" {level3} ")
    common = fixture_items("common_3379778.json")[0]
    intro = fixture_items("intro_3379778.json")[0]
    record = normalize_festival(listing, common, intro, today=TODAY)
    assert (record.source_class_level1, record.source_class_level2, record.source_class_code) == (
        "EV", level2 or None, level3 or None,
    )
    assert record.category == category
    assert record.publishable is (category == "festival")
    assert record.review_status == ("approved" if record.publishable else "pending")
    assert record.issues == ([] if record.publishable else ["not_festival_class"])


def test_I6_detail_text_and_homepage(listing: dict[str, Any]) -> None:
    common = {"overview": " <b>첫 줄</b><br />둘째 줄<br> <br><BR>끝 &amp; 확인 ", "homepage": "https://fallback"}
    intro = {
        "eventhomepage": '<a href="https://x">이동</a><a href="https://y">다른 사이트</a>',
        "eventplace": " 가락몰 ",
        "sponsor1": " 주최 단체 ",
        "usetimefestival": " <b>무료</b>  (일부 유료) ",
    }
    record = normalize_festival(listing, common, intro, today=TODAY)
    assert record.summary == "첫 줄\n둘째 줄\n\n끝 & 확인"
    assert record.venue_name == "가락몰"
    assert record.address == f"{listing['addr1']} {listing['addr2']}"
    assert record.organizer == "주최 단체"
    assert record.official_url == "https://x"
    assert record.admission_fee_text == "무료  (일부 유료)"


def test_I6_blank_fields_and_summary_limit(listing: dict[str, Any]) -> None:
    listing["addr2"] = ""
    common = {"overview": "가" * 2001, "homepage": "https://fallback"}
    intro = {"usetimefestival": "  <b> </b> ", "eventplace": "", "sponsor1": ""}
    record = normalize_festival(listing, common, intro, today=TODAY)
    assert record.summary == "가" * 2000
    assert record.address == listing["addr1"]
    assert record.admission_fee_text is record.venue_name is record.organizer is None
    assert record.official_url == "https://fallback"
    intro["eventhomepage"] = '<a href="javascript:void(0)">이동</a>'
    assert normalize_festival(listing, common, intro, today=TODAY).official_url is None


def test_I6_missing_intro_keeps_common_fields(listing: dict[str, Any]) -> None:
    common = {"overview": "소개", "homepage": "https://release"}
    record = normalize_festival(listing, common, today=TODAY)
    assert record.issues == ["detail_missing"]
    assert record.summary == "소개"
    assert record.official_url == "https://release"
    assert record.venue_name is record.organizer is record.admission_fee_text is None
    assert record.publishable


@pytest.mark.parametrize(
    ("changes", "expected_status", "issues"),
    [
        ({}, "ongoing", []),
        ({"mapx": "117"}, "ongoing", ["coords_out_of_range"]),
        ({"eventstartdate": ""}, "needs_review", ["date_invalid"]),
        ({"title": " "}, "ongoing", ["title_missing"]),
        ({"lDongRegnCd": "99"}, "ongoing", ["region_unknown"]),
    ],
)
def test_I7_publication_requirements(
    listing: dict[str, Any], changes: dict[str, str], expected_status: str, issues: list[str]
) -> None:
    record = normalize_festival(listing | changes, today=TODAY, details_requested=False)
    assert record.publishable is (not issues)
    assert record.review_status == ("pending" if issues else "approved")
    assert record.event_status == expected_status
    assert record.issues == issues
