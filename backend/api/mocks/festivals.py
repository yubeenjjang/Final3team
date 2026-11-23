from datetime import date

from api.schemas.festivals import (
    CopyrightType,
    FestivalDetail,
    FestivalStatus,
    ImageCopyright,
    RegionCode,
)

_IMAGE_BASE = "https://tong.visitkorea.or.kr/cms/resource/mock"
_IMAGE_CREDIT = "한국관광공사"


def _festival(
    source_ref: str,
    name: str,
    region_code: RegionCode,
    venue_name: str | None,
    lat: float | None,
    lng: float | None,
    start_date: date | None,
    end_date: date | None,
    event_status: FestivalStatus,
    copyright_type: CopyrightType | None = None,
    fee_text: str | None = None,
) -> FestivalDetail:
    festival_id = f"fst_{source_ref}"
    image_path = f"{_IMAGE_BASE}/{festival_id}"
    image_copyright = None
    if copyright_type is not None:
        image_copyright = ImageCopyright(
            type=copyright_type,
            credit=_IMAGE_CREDIT,
            modify_allowed=copyright_type == "Type1",
        )
    return FestivalDetail(
        festival_id=festival_id,
        name=name,
        region_code=region_code,
        venue_name=venue_name,
        lat=lat,
        lng=lng,
        start_date=start_date,
        end_date=end_date,
        event_status=event_status,
        thumbnail_url=f"{image_path}_2.jpg" if image_copyright else None,
        image_credit=_IMAGE_CREDIT if image_copyright else None,
        last_synced_at="2026-11-22T09:00:00+09:00",
        address=f"{venue_name} 일대" if venue_name else None,
        overview=f"{name} 소개(모의)",
        fee_text=fee_text,
        homepage_url=None,
        image_url=f"{image_path}_1.jpg" if image_copyright else None,
        image_copyright=image_copyright,
        source_ref=source_ref,
    )


FESTIVALS = (
    _festival(
        "000001", "광화문 겨울빛 축제", "SEOUL", "광화문광장", 37.5759, 126.9768,
        date(2026, 11, 20), date(2026, 12, 31), "ongoing", "Type3", "무료",
    ),
    _festival(
        "000002", "한강 겨울 야시장", "SEOUL", "여의도 한강공원", 37.5284, 126.9327,
        date(2026, 12, 5), date(2026, 12, 7), "upcoming", "Type1",
    ),
    _festival(
        "000003", "부산 빛 축제", "BUSAN", "광복로 일대", 35.1003, 129.0337,
        date(2026, 11, 15), date(2026, 11, 30), "ongoing", "Type3", "무료",
    ),
    _festival(
        "000004", "해운대 모래 축제", "BUSAN", "해운대해수욕장", 35.1587, 129.1604,
        date(2026, 6, 1), date(2026, 6, 3), "ended", "Type3",
    ),
    _festival(
        "000005", "평창 송어 축제", "GANGWON", "오대천 일원", 37.5640, 128.3846,
        date(2026, 12, 26), date(2027, 1, 25), "upcoming",
    ),
    _festival(
        "000006", "장소 미정 축제", "GYEONGGI", None, None, None,
        None, None, "needs_review",
    ),
)
