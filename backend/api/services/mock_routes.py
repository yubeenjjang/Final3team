import json
import secrets
import string
from datetime import datetime, timedelta, timezone

from api.errors import ApiError
from api.mocks.store import RouteRecord, route_lock, route_request_keys, route_requests
from api.schemas.festivals import FestivalDetail
from api.schemas.routes import (
    Endpoint,
    FestivalEndpoint,
    PlaceEndpoint,
    ReturnRouteRequest,
    RouteDirection,
    RouteRequest,
    RouteStatus,
)
from api.services.festival_lookup import find_festival
from api.services.notice_lookup import control_reader
from api.services.notices import CONTROL_CHANGED_CODE, CONTROL_CHANGED_MESSAGE, ControlSnapshot
from ulid import ULID

_ALPHABET = string.ascii_letters + string.digits
_KST = timezone(timedelta(hours=9))
_CONTROL_NOTICE = "공식 교통통제 반영 여부를 확인하지 못했어요."
_SECONDARY_NOTICE = "2차 공급원(카카오맵) 결과예요. 이 결과는 저장하지 않아 다시 보려면 새로 조회해야 해요."
_RETRY_AFTER_S = 2
_FINAL_STATUSES: dict[str, RouteStatus] = {
    "async_ready": "ready",
    "sync_ready": "ready",
    "async_bus_ready": "ready",
    "sync_bus_ready": "ready",
    "sync_secondary": "unavailable",
    "async_unavailable": "unavailable",
    "async_timeout": "timed_out",
    "async_secondary_sync_only": "unavailable",
    "async_no_result": "unavailable",
    "async_quota_exceeded": "unavailable",
    "overloaded": "rejected",
}
_SECONDARY_FAILURE = ("ROUTE_SECONDARY_SYNC_ONLY", "잠시 뒤 다시 조회해 주세요.", True)
_FAILURES: dict[str, tuple[str, str, bool]] = {
    "async_unavailable": ("ROUTE_UPSTREAM_ERROR", "경로 정보를 가져오지 못했어요.", True),
    "async_timeout": ("ROUTE_TIMEOUT", "경로를 찾는 시간이 초과됐어요.", True),
    "sync_secondary": _SECONDARY_FAILURE,
    "async_secondary_sync_only": _SECONDARY_FAILURE,
    "async_no_result": ("ROUTE_NO_RESULT", "조건에 맞는 경로가 없어요.", False),
    "async_quota_exceeded": (
        "ROUTE_QUOTA_EXCEEDED", "오늘 조회 한도를 다 썼어요. 공식 교통 안내를 확인해 주세요.", False,
    ),
}

Coordinates = tuple[float, float]


def _now() -> str:
    return datetime.now(_KST).isoformat()


def _random_id(prefix: str, length: int) -> str:
    return prefix + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _new_id(prefix: str) -> str:
    """자원 ID: 접두사_ + ULID(26자). 토큰에는 쓰지 않는다(시간 기반이라 추측 가능)."""
    return prefix + str(ULID())


def _validate_endpoints(request: RouteRequest, festival: FestivalDetail) -> None:
    endpoints = (request.origin, request.destination)
    uses_festival = any(isinstance(endpoint, FestivalEndpoint) for endpoint in endpoints)
    if uses_festival and (festival.lat is None or festival.lng is None):
        raise ApiError(400, "FESTIVAL_LOCATION_UNKNOWN", "축제 장소의 좌표를 알 수 없어요.")
    if any(
        isinstance(endpoint, PlaceEndpoint) and "없는곳" in (endpoint.query or "")
        for endpoint in endpoints
    ):
        raise ApiError(400, "ROUTE_INVALID", "목적지를 찾을 수 없어요")


def _register_route(
    direction: RouteDirection,
    request: RouteRequest,
    body: dict[str, object],
    scenario: str,
) -> RouteRecord:
    with route_lock:
        festival = find_festival(request.festival_id)
        if festival is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없어요.")
        _validate_endpoints(request, festival)

        submitted_body = json.dumps(body, sort_keys=True)
        request_key = (direction, request.request_id)
        existing_id = route_request_keys.get(request_key)
        if existing_id is not None:
            existing = route_requests[existing_id]
            if existing.body != submitted_body:
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")
            return existing

        final_status = _FINAL_STATUSES.get(scenario)
        if final_status is None:
            raise ApiError(422, "VALIDATION_ERROR", "X-Mock-Scenario 값을 확인해 주세요.")

        route_id = _new_id("rr_")
        while route_id in route_requests:
            route_id = _new_id("rr_")
        record = RouteRecord(
            route_request_id=route_id,
            access_token=_random_id("rrt_", 24),
            direction=direction,
            request=request,
            festival=festival,
            body=submitted_body,
            scenario=scenario,
            status="queued" if scenario.startswith("async_") else final_status,
            updated_at=_now(),
            control_version=control_reader().snapshot(festival.festival_id).version,
        )
        route_requests[route_id] = record
        route_request_keys[request_key] = route_id
        return record


def create_route(
    direction: RouteDirection,
    request: RouteRequest,
    body: dict[str, object],
    scenario: str,
) -> tuple[int, dict[str, object]]:
    record = _register_route(direction, request, body, scenario)
    control = control_reader().snapshot(record.festival.festival_id)
    if record.control_version != control.version:
        return 200, _control_changed(record, control)
    if record.scenario == "overloaded":
        raise ApiError(503, "ROUTE_OVERLOADED", "경로 요청이 많아요. 잠시 후 다시 시도해 주세요.", True)
    if record.scenario in ("sync_ready", "sync_bus_ready", "sync_secondary"):
        return 200, _ready_payload(record, control)
    return 202, {
        "route_request_id": record.route_request_id,
        "route_status": "queued",
        "status_url": f"/api/v1/routes/{direction}/{record.route_request_id}",
        "route_access_token": record.access_token,
        "retry_after_s": _RETRY_AFTER_S,
        "is_mock": True,
    }


def create_ready_route(festival_id: str, destination_query: str) -> tuple[str, str]:
    request = ReturnRouteRequest(
        request_id=_new_id("req_"),
        festival_id=festival_id,
        destination=PlaceEndpoint(query=destination_query),
    )
    record = _register_route("return", request, request.model_dump(mode="json"), "sync_ready")
    return record.route_request_id, record.access_token


def verify_return_route_token(route_id: str, token: str | None) -> None:
    with route_lock:
        route = route_requests.get(route_id)
        if (
            not token or route is None or route.direction != "return"
            or not secrets.compare_digest(token.encode(), route.access_token.encode())
        ):
            raise ApiError(403, "FORBIDDEN", "이 경로에 접근할 수 없어요.")


def return_selection_token(route_id: str) -> str:
    with route_lock:
        return route_requests[route_id].access_token


def get_route(
    direction: RouteDirection, route_request_id: str, access_token: str | None
) -> dict[str, object]:
    if not access_token:
        raise ApiError(401, "UNAUTHORIZED", "경로 조회 토큰을 보내 주세요.")
    with route_lock:
        record = route_requests.get(route_request_id)
        if record is None or record.direction != direction:
            raise ApiError(404, "ROUTE_REQUEST_NOT_FOUND", "경로 요청을 찾을 수 없어요.")
        if not secrets.compare_digest(access_token.encode(), record.access_token.encode()):
            raise ApiError(403, "FORBIDDEN", "이 경로를 조회할 수 없는 토큰입니다.")

        control = control_reader().snapshot(record.festival.festival_id)
        if record.control_version != control.version:
            return _control_changed(record, control)
        if record.status == "queued":
            record.status = "processing"
            record.updated_at = _now()
        elif record.status == "processing":
            record.status = _FINAL_STATUSES[record.scenario]
            record.updated_at = _now()
        return _status_payload(record, control)


def _control_changed(record: RouteRecord, control: ControlSnapshot) -> dict[str, object]:
    return {
        "route_request_id": record.route_request_id,
        "route_status": "unavailable",
        "completed_valid_route": False,
        "updated_at": _now(),
        "is_mock": True,
        "error": {"code": CONTROL_CHANGED_CODE, "message": CONTROL_CHANGED_MESSAGE, "retryable": True},
        "notices": control.apply_to([CONTROL_CHANGED_MESSAGE], record.festival.festival_id),
    }


def _status_payload(record: RouteRecord, control: ControlSnapshot) -> dict[str, object]:
    status = record.status
    body: dict[str, object] = {
        "route_request_id": record.route_request_id,
        "route_status": status,
        "completed_valid_route": status == "ready",
        "updated_at": record.updated_at,
        "is_mock": True,
    }
    if status == "ready":
        body.update(_ready_payload(record, control))
    elif status in ("queued", "processing"):
        body["retry_after_s"] = _RETRY_AFTER_S
    elif status in ("unavailable", "timed_out"):
        code, message, retryable = _FAILURES[record.scenario]
        body["error"] = {"code": code, "message": message, "retryable": retryable}
        body["notices"] = [message]
    return body


def _format_endpoint(endpoint: Endpoint, festival: FestivalDetail) -> dict[str, object]:
    if isinstance(endpoint, FestivalEndpoint):
        return {"type": "festival", "name": festival.venue_name, "lat": festival.lat, "lng": festival.lng}
    label = endpoint.query if endpoint.query is not None else f"{endpoint.lat},{endpoint.lng}"
    return {"type": "place", "label": label}


def _coordinates(
    endpoint: Endpoint, festival: FestivalDetail, fallback: Coordinates
) -> Coordinates:
    if isinstance(endpoint, FestivalEndpoint):
        lat, lng = festival.lat, festival.lng
    else:
        lat, lng = endpoint.lat, endpoint.lng
    if lat is not None and lng is not None:
        return lat, lng
    return fallback


def _candidate(
    request: RouteRequest, festival: FestivalDetail, *, secondary: bool, demo_bus: bool = False,
) -> dict[str, object]:
    # 검색어 장소의 좌표는 외부 조회 없이 고정 좌표로 표시한다.
    start = _coordinates(request.origin, festival, (37.5547, 126.9707))
    end = _coordinates(request.destination, festival, (37.5641, 126.9839))
    first = tuple(round(a + (b - a) / 3, 6) for a, b in zip(start, end))
    second = tuple(round(b - (b - a) / 3, 6) for a, b in zip(start, end))
    bus_crowding = {"status": "unverified", "reason": "모의 응답"}
    if secondary:
        bus_crowding = {
            "status": "unsupported",
            "reason": "2차 공급원은 버스 혼잡 근거를 주지 않아요(모의)",
        }
    transit = {"mode": "subway", "line": "(모의)", "duration_min": 24, "path": [first, second]}
    if demo_bus:
        transit.update(mode="bus", line="753", stops=[
            {"id": "123456", "name": "예시 승차 정류장", "lat": first[0], "lng": first[1]},
            {"id": "123457", "name": "예시 다음 정류장", "lat": second[0], "lng": second[1]},
        ])
    return {
        "candidate_id": "c1",
        "summary": "버스 1회(모의)" if demo_bus else "지하철 1회 환승(모의)",
        "duration_min": 38,
        "distance_m": 9200,
        "walk_m": 650,
        "transfers": 1,
        "fare_krw": 1550,
        "legs": [
            {"mode": "walk", "duration_min": 6, "path": [start, first]},
            transit,
            {"mode": "walk", "duration_min": 8, "path": [second, end]},
        ],
        "service_running": True,
        "score": None,
        "area_evidence": {"crowd_areas": [], "traffic_incidents": []},
        "mode_evidence": {"bus_crowding": bus_crowding},
    }


def _ready_payload(record: RouteRecord, control: ControlSnapshot) -> dict[str, object]:
    request, festival = record.request, record.festival
    secondary = record.scenario == "sync_secondary"
    constraints = request.user_constraints
    constraint_status = {"control": "unverified"}
    if constraints.with_child:
        constraint_status["with_child"] = "not_verifiable"
    if constraints.wheelchair:
        constraint_status["wheelchair"] = "not_verifiable"
    if constraints.max_walk_m is not None:
        constraint_status["max_walk_m"] = "not_verifiable"
    return {
        "route_request_id": record.route_request_id,
        "route_status": "ready",
        "direction": record.direction,
        "festival_id": festival.festival_id,
        "origin": _format_endpoint(request.origin, festival),
        "destination": _format_endpoint(request.destination, festival),
        "travel_mode": request.travel_mode,
        "route_preference": request.route_preference,
        "route_candidates": [_candidate(
            request, festival, secondary=secondary,
            demo_bus=record.direction == "return" and record.scenario in ("sync_bus_ready", "async_bus_ready"),
        )],
        "provider": "kakao" if secondary else "mock_adapter",
        "provider_tier": "secondary" if secondary else "mock",
        "queried_at": record.updated_at,
        "verification_status": "control_unverified",
        "completed_valid_route": True,
        "constraint_status": constraint_status,
        "coverage": {"scope": "national", "region_code": festival.region_code, "supported": True},
        "score_version": None,
        "notices": control.apply_to(
            [_CONTROL_NOTICE, _SECONDARY_NOTICE] if secondary else [_CONTROL_NOTICE], festival.festival_id,
        ),
        "is_mock": True,
    }
