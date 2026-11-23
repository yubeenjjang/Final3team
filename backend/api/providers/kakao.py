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
