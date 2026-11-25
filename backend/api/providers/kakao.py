import re
from datetime import datetime
from typing import Any

import httpx2

from api.providers.route_base import (
    KST,
    ProviderError,
    ProviderResult,
    RouteProviderClient,
    RouteQuery,
    make_candidate,
    minutes,
)

_BASE_URL = httpx2.URL(scheme="https", host="dapi.kakao.com")
_NOTICES = (
    "2차 공급원(카카오맵) 결과예요. 이 결과는 저장하지 않아 다시 보려면 새로 조회해야 해요.",
    "첫·끝 도보 정보가 없어요",
    "막차 확인 불가",
)
_METROPOLITAN_CITIES = {"서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"}
_PROVINCES = {
    "경기": "경기도", "강원": "강원도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전라북도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주도",
}
_REGION_NAMES = {**_PROVINCES, **{name: name for name in _PROVINCES.values()},
                 "강원특별자치도": "강원도", "전북특별자치도": "전라북도", "제주특별자치도": "제주도"}
_REGION_NAMES.update({
    f"{city}{suffix}": city for city in _METROPOLITAN_CITIES
    for suffix in ("", "특별시", "광역시", "특별자치시")
})
_REGION_NAMES.update({f"{city}시": city for city in _METROPOLITAN_CITIES - {"광주"}})


def _municipality(address: str) -> tuple[str | None, tuple[str, ...]]:
    parts = address.replace(",", " ").split()
    region = _REGION_NAMES.get(parts[0]) if parts else None
    local = parts[1:] if region else parts
    if not local or not re.fullmatch(r"[가-힣]+[시군구]", local[0]):
        return region, ()
    if local[0].endswith("시") and len(local) > 1 and re.fullmatch(r"[가-힣]+구", local[1]):
        return region, tuple(local[:2])
    return region, (local[0],)


def _same_municipality(query: str, result: str) -> bool:
    region, local = _municipality(query)
    result_region, result_local = _municipality(result)
    return (
        (bool(local) or region in _METROPOLITAN_CITIES)
        and (region is None or region == result_region)
        and result_local[:len(local)] == local
    )


class KakaoClient(RouteProviderClient):
    provider = "kakao"
    _key_env = "KAKAO_REST_API_KEY"
    _timeout = 3.0

    def query(self, query: RouteQuery) -> ProviderResult:
        queried_at = datetime.now(KST).isoformat()
        start_lat, start_lng = query.origin
        end_lat, end_lng = query.destination
        body = self._get(
            "/v2/routing/publictraffic",
            {"start_x": start_lng, "start_y": start_lat, "end_x": end_lng, "end_y": end_lat},
        )
        status = body.get("status")
        if status == "INVALID_REQUEST":
            raise ProviderError("bad_request", self.provider)
        if status in ("NO_RESULTS", "STARTNODES_NULL", "ENDNODES_NULL", "EQUAL_POINTS"):
            raise ProviderError("no_result", self.provider)
        routes = body.get("routes")
        if not routes:
            raise ProviderError("no_result", self.provider)
        if not isinstance(routes, list):
            raise ProviderError("temporary", self.provider)
        try:
            candidates = [
                _candidate(index, entry) for index, entry in enumerate(routes[:3], start=1)
            ]
        except (AttributeError, KeyError, OverflowError, TypeError, ValueError):
            candidates = []
        if not candidates:
            raise ProviderError("temporary", self.provider)
        return ProviderResult(self.provider, "secondary", queried_at, candidates, list(_NOTICES))

    def search_place(self, query: str) -> tuple[float, float, str]:
        body = self._get("/v2/local/search/keyword.json", {"query": query, "size": 1})
        documents = body.get("documents")
        if not documents:
            raise ProviderError("no_result", self.provider)
        try:
            return float(documents[0]["y"]), float(documents[0]["x"]), query
        except (KeyError, OverflowError, TypeError, ValueError):
            pass
        raise ProviderError("temporary", self.provider)

    def search_address(self, address: str) -> tuple[float, float]:
        body = self._get("/v2/local/search/address.json", {"query": address, "size": 1})
        documents = body.get("documents")
        if not isinstance(documents, list) or not documents or not isinstance(documents[0], dict):
            raise ProviderError("no_result", self.provider)

        document = documents[0]
        if not any(
            _same_municipality(address, part["address_name"])
            for part in (document.get("road_address"), document.get("address"), document)
            if isinstance(part, dict) and isinstance(part.get("address_name"), str)
        ):
            raise ProviderError("no_result", self.provider)
        try:
            return float(document["y"]), float(document["x"])
        except (KeyError, OverflowError, TypeError, ValueError):
            raise ProviderError("temporary", self.provider) from None

    def _get(self, path: str, params: dict[str, str | float | int]) -> dict[str, Any]:
        status, body = self._request_json(
            "GET",
            _BASE_URL.copy_with(path=path),
            params=params,
            headers={"Authorization": f"KakaoAK {self._key}"},
        )
        if status == 400:
            kind = "quota" if body.get("code") in (-10, "-10") else "bad_request"
            raise ProviderError(kind, self.provider)
        return body


def _leg(step: dict[str, Any]) -> dict[str, Any]:
    properties = step["properties"]
    normalized = {
        "mode": {"WALK": "walk", "BUS": "bus", "SUBWAY": "subway"}[properties["type"]],
        "duration_min": minutes(properties["time"]),
        "path": [[float(lat), float(lng)] for lng, lat in (step.get("path") or {}).get("points", [])],
    }
    vehicles = properties.get("vehicles")
    if vehicles and vehicles[0].get("name"):
        normalized["line"] = vehicles[0]["name"]
    stops = properties.get("stops")
    if stops is not None:
        normalized["stops"] = [{"name": stop["name"]} for stop in stops]
    return normalized


def _candidate(index: int, route: dict[str, Any]) -> dict[str, object]:
    properties = route["properties"]
    return make_candidate(
        index,
        duration_min=minutes(properties["totalTime"]),
        distance_m=properties["totalDistance"],
        walk_m=None,
        transfers=properties["transfers"],
        fare_krw=properties["fare"]["value"],
        legs=[_leg(step) for step in route["steps"]],
        service_running=None,
        bus_crowding={"status": "unsupported", "reason": "2차 공급원은 버스 혼잡 근거를 주지 않아요"},
    )
