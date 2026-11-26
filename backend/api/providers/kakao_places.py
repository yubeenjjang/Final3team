import asyncio
import os

import httpx2

from api.providers.transit_arrivals import distance_m
from api.schemas.festival_info import FacilityCategory, FacilityItem

_URL = "https://dapi.kakao.com/v2/local/search/category.json"
_CODES = {"food": "FD6", "attraction": "AT4"}
# 공공데이터(DB)에 없는 지역에서만 쓰는 보충 분류. 버스정류장·화장실·응급실·택시는 카카오 분류가 없다.
FALLBACK_CODES = {"subway_station": "SW8", "parking": "PK6", "hospital": "HP8"}


async def nearby_places(
    category: FacilityCategory, lat: float, lng: float, radius_m: int, limit: int,
) -> list[FacilityItem] | None:
    key = os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        return None
    items: list[FacilityItem] = []
    try:
        async with asyncio.timeout(3.0), httpx2.AsyncClient(timeout=3.0) as client:
            for page in range(1, min(4, (limit + 14) // 15) + 1):
                response = await client.get(_URL, headers={"Authorization": f"KakaoAK {key}"}, params={
                    "category_group_code": _CODES.get(category) or FALLBACK_CODES[category], "x": lng, "y": lat,
                    "radius": radius_m, "sort": "distance", "size": 15, "page": page,
                })
                response.raise_for_status()
                body = response.json()
                documents = body.get("documents")
                if not isinstance(documents, list):
                    return None
                for doc in documents:
                    try:
                        place_lat, place_lng = float(doc["y"]), float(doc["x"])
                        place_id, name = str(doc["id"]), str(doc["place_name"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    if not (33 <= place_lat <= 39 and 124 <= place_lng <= 132 and place_id and name):
                        continue
                    distance = round(distance_m(lat, lng, place_lat, place_lng), 1)
                    if distance <= radius_m:
                        items.append(FacilityItem(
                            facility_id=f"kakao:{place_id}", category=category, name=name,
                            lat=place_lat, lng=place_lng, distance_m=distance,
                            address=doc.get("road_address_name") or doc.get("address_name"),
                            source="kakao_local",
                        ))
                if body.get("meta", {}).get("is_end", True):
                    break
    except (TimeoutError, httpx2.HTTPError, ValueError, TypeError, KeyError):
        return None
    items.sort(key=lambda item: (item.distance_m, item.facility_id))
    return items[:limit]
