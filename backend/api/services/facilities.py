import os

from sqlalchemy.exc import SQLAlchemyError

from api.errors import ApiError
from api.providers import kakao_places
from api.providers.transit_arrivals import distance_m
from api.repositories.festival_info import nearby_facility_items
from api.schemas.festival_info import (
    Coverage, FacilitiesResponse, FacilityCategory, InfoStatus, SourceError,
)
from api.services.festival_lookup import find_festival

DEFAULT_CATEGORIES: tuple[FacilityCategory, ...] = (
    "toilet", "parking", "hospital", "emergency", "subway_station", "bus_stop",
    "bike_zone", "taxi_stand", "food", "attraction",
)
_ALL_CATEGORIES = set(DEFAULT_CATEGORIES) | {"locker", "pharmacy"}
_DB_CATEGORIES = set(DEFAULT_CATEGORIES) - {"food", "attraction"}


def parse_categories(value: str | None) -> list[FacilityCategory]:
    if value is None:
        return list(DEFAULT_CATEGORIES)
    categories = [part.strip() for part in value.split(",")]
    if not categories or any(not part or part not in _ALL_CATEGORIES for part in categories):
        raise ApiError(422, "INVALID_CATEGORIES", "시설 분류를 확인해 주세요.")
    return list(dict.fromkeys(categories))  # type: ignore[return-value]


async def get_facilities(
    festival_id: str, categories: list[FacilityCategory], radius_m: int, limit_per_category: int,
) -> FacilitiesResponse:
    festival = await find_festival(festival_id)
    if festival is None:
        raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없습니다.")
    real = os.environ.get("FACILITIES_PROVIDER", "mock") == "real"
    response = FacilitiesResponse(
        festival_id=festival_id, is_mock=not real, source="facilities_db" if real else "mock",
        coverage=Coverage(scope="national", region_code=festival.region_code, supported=True),
    )
    if festival.lat is None or festival.lng is None or not (33 <= festival.lat <= 39 and 124 <= festival.lng <= 132):
        response.status = "unavailable"
        response.error = SourceError(code="FESTIVAL_LOCATION_UNKNOWN", message="축제 위치를 확인할 수 없어요.", retryable=False)
        return response
    response.categories_status = {
        category: "unsupported" if category in {"locker", "pharmacy"} else "unverified"
        for category in categories
    }
    db_categories = [category for category in categories if category in _DB_CATEGORIES]
    kakao_used = False
    if not real:
        response.notices.append("시설 위치 DB 조회가 비활성화되어 있어요.")
        response.status = "unverified"
        return response
    if db_categories:
        try:
            rows = await nearby_facility_items(festival.lat, festival.lng, radius_m, db_categories)
        except (SQLAlchemyError, RuntimeError, ValueError):
            for category in db_categories:
                response.categories_status[category] = "unavailable"
            response.status = "unavailable"
            response.error = SourceError(code="SOURCE_RESULT_ERROR", message="시설 위치를 조회할 수 없어요.", retryable=True)
            return response
        grouped = {category: [] for category in db_categories}
        for row in rows:
            if row.category not in grouped or not (33 <= row.lat <= 39 and 124 <= row.lng <= 132):
                continue
            row.distance_m = round(distance_m(festival.lat, festival.lng, row.lat, row.lng), 1)
            if row.distance_m <= radius_m:
                grouped[row.category].append(row)
        for category, items in grouped.items():
            items.sort(key=lambda item: (item.distance_m, item.facility_id))
            response.items.extend(items[:limit_per_category])
            response.categories_status[category] = "ok" if items else "unverified"
        # 시설 DB(서울 공공데이터)가 비어 있는 지역은 지하철역·주차장·병원만 카카오로 보충한다.
        # 보충 실패는 DB 조회 결과(미확인)를 그대로 두고 응답 전체를 실패로 만들지 않는다.
        for category, items in grouped.items():
            if items or category not in kakao_places.FALLBACK_CODES:
                continue
            places = await kakao_places.nearby_places(category, festival.lat, festival.lng, radius_m, limit_per_category)
            if places:
                response.items.extend(places)
                response.categories_status[category] = "ok"
                kakao_used = True
    # Kakao place results are relayed only in this response, never written to DB or cache.
    for category in ("food", "attraction"):
        if category not in categories:
            continue
        places = await kakao_places.nearby_places(category, festival.lat, festival.lng, radius_m, limit_per_category)
        if places is None:
            response.categories_status[category] = "unavailable"
        else:
            response.items.extend(places)
            response.categories_status[category] = "ok" if places else "unverified"
    if any(status == "unavailable" for status in response.categories_status.values()):
        response.status = "unavailable"
    elif not response.items:
        response.status = "unverified"
    if kakao_used or any(category in categories for category in ("food", "attraction")):
        response.notices.append("카카오 장소 결과는 저장하지 않으며 새로 조회하면 달라질 수 있어요.")
    return response
