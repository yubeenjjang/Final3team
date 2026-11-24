import asyncio
import hmac
import json
import os
import secrets
from base64 import b32encode
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Protocol

from sqlalchemy import RowMapping

from api.errors import ApiError
from api.providers.kakao import KakaoClient
from api.providers.quota import QuotaGuard, QuotaProvider
from api.providers.route_base import (
    KST,
    Coordinates,
    ErrorKind,
    ProviderError,
    ProviderName,
    ProviderResult,
    RouteQuery,
    as_kst,
)
from api.providers.tmap import SERVICE_ENDED_NOTICE, TmapClient
from api.repositories.route_store import RouteStore, stored_candidates, token_hash
from api.schemas.festivals import FestivalDetail
from api.schemas.routes import Endpoint, FestivalEndpoint, RouteDirection, RouteRequest, RouteStatus
from api.services.festival_lookup import find_festival
from api.services.mock_routes import (
    _CONTROL_NOTICE,
    _FAILURES,
    _RETRY_AFTER_S,
    _format_endpoint,
    _random_id,
)

_SYNC_WAIT_S = 3
_REQUEST_LIMIT_S = 10
_FLIGHT_LIMIT_S = 12
_CACHE_TTL_S = 60
_STARTUP_SECRET = secrets.token_bytes(32)


@dataclass(frozen=True)
class _Failure:
    code: str
    message: str
    retryable: bool = False
    status: RouteStatus = "unavailable"
    http_status: int = 200
    notices: tuple[str, ...] = ()


_UPSTREAM_ERROR = _Failure(*_FAILURES["async_unavailable"])
_TIMEOUT = _Failure(*_FAILURES["async_timeout"], status="timed_out")
_SECONDARY_ONLY = _Failure(*_FAILURES["async_secondary_sync_only"])
_QUOTA_EXCEEDED = _Failure(*_FAILURES["async_quota_exceeded"])
_RESULT_EXPIRED = _Failure("ROUTE_RESULT_EXPIRED", "경로가 만료됐어요. 다시 조회해 주세요.", True)
_DB_RESULT_EXPIRED = replace(_RESULT_EXPIRED, retryable=False)
_ACCESS_EXPIRED = _Failure("ROUTE_ACCESS_EXPIRED", "경로 조회 시간이 지났어요. 새 요청 ID로 다시 요청해 주세요.")
_DB_UNAVAILABLE = _Failure(
    "ROUTE_STORE_UNAVAILABLE", "귀가 요청 저장소에 연결할 수 없어요.", True, http_status=503,
)
_PROVIDER_FAILURES: dict[ErrorKind, _Failure] = {
    "too_close": _Failure("ROUTE_NO_RESULT", "걸어서 갈 수 있는 거리예요"),
    "no_result": _Failure(*_FAILURES["async_no_result"]),
    "service_ended": _Failure(
        "ROUTE_NO_RESULT", "지금은 대중교통으로 갈 수 없어요",
        notices=(SERVICE_ENDED_NOTICE,),
    ),
    "bad_request": _Failure("ROUTE_INVALID", "출발지와 도착지를 확인해 주세요."),
    "timeout": _TIMEOUT,
}


class _TransitProvider(Protocol):
    def query(self, query: RouteQuery) -> ProviderResult: ...


class _KakaoProvider(_TransitProvider, Protocol):
    def search_place(self, query: str) -> tuple[float, float, str]: ...


class _Quota(Protocol):
    def try_acquire(self, provider: QuotaProvider) -> bool: ...


@dataclass
class _CachedRoute:
    key: str
    valid_until: datetime
    result: ProviderResult | None = field(repr=False)


@dataclass
class _RouteRecord:
    route_id: str
    access_token: str = field(repr=False)
    direction: RouteDirection
    request: RouteRequest = field(repr=False)
    body: str = field(repr=False)
    depart_at: datetime
    updated_at: datetime
    sync_deadline: float
    deadline: float
    accepted: bool = False
    task: asyncio.Task[ProviderResult | None] | None = field(default=None, repr=False)
    festival: FestivalDetail | None = None
    cached: _CachedRoute | None = None
    failure: _Failure | None = None
    route_key: str | None = None
    source_type: str = "fresh"

    @property
    def request_key(self) -> tuple[RouteDirection, str]:
        return self.direction, self.request.request_id


_FlightResult = _CachedRoute | ProviderResult | _Failure


def uses_real_routes() -> bool:
    return os.environ.get("ROUTE_PROVIDER") == "real"


class RealRouteService:
    def __init__(
        self,
        *,
        tmap: Callable[[], _TransitProvider] = TmapClient,
        kakao: Callable[[], _KakaoProvider] = KakaoClient,
        quota: _Quota | None = None,
        now: Callable[[], datetime] | None = None,
        store: RouteStore | None = None,
    ) -> None:
        self._tmap = tmap
        self._kakao = kakao
        self._clock = now if now is not None else lambda: datetime.now(KST)
        self._quota = quota if quota is not None else QuotaGuard(now=self._now)
        secret = os.environ.get("ROUTE_KEY_SECRET")
        if store is not None and not secret:
            raise ApiError(503, "ROUTE_STORE_UNAVAILABLE", "귀가 저장소 설정을 확인해 주세요.", True)
        self._secret = secret.encode() if secret else _STARTUP_SECRET
        self._store = store
        self._records: dict[str, _RouteRecord] = {}
        self._request_keys: dict[tuple[RouteDirection, str], _RouteRecord] = {}
        self._cache: dict[str, _CachedRoute] = {}
        self._flights: dict[str, asyncio.Task[_FlightResult]] = {}

    async def create_route(
        self, direction: RouteDirection, request: RouteRequest, body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        submitted_body = json.dumps(body, sort_keys=True)
        if self._store is not None:
            return await self._create_db_route(direction, request, submitted_body)

        record = self._request_keys.get((direction, request.request_id))
        if record is None:
            record = self._register(direction, request, submitted_body)
        elif record.body != submitted_body:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")
        return await self._submit_registered(record)

    async def _submit_registered(self, record: _RouteRecord) -> tuple[int, dict[str, object]]:
        secondary = None
        task = record.task
        if task is not None and not record.accepted:
            remaining = max(0, record.sync_deadline - asyncio.get_running_loop().time())
            done, _ = await asyncio.wait((task,), timeout=remaining)
            if done:
                secondary = task.result()
            else:
                record.accepted = True

        if record.accepted:
            return 202, self._accepted_payload(record)
        result = secondary or self._record_result(record)
        if result is not None:
            return 200, self._ready_payload(record, result)
        failure = record.failure
        if failure is not None and failure.http_status != 200:
            raise ApiError(failure.http_status, failure.code, failure.message, failure.retryable)
        return 200, {**self._status_payload(record), "route_access_token": record.access_token}

    async def get_route_response(
        self, direction: RouteDirection, route_id: str, access_token: str | None,
    ) -> dict[str, object]:
        if self._store is not None:
            return await asyncio.to_thread(self.get_route, direction, route_id, access_token)
        return self.get_route(direction, route_id, access_token)

    def get_route(
        self, direction: RouteDirection, route_id: str, access_token: str | None
    ) -> dict[str, object]:
        if not access_token:
            raise ApiError(401, "UNAUTHORIZED", "경로 조회 토큰을 보내 주세요.")
        if self._store is not None:
            return self._db_status(direction, route_id, access_token)[1]
        record = self._records.get(route_id)
        if record is None or record.direction != direction:
            raise ApiError(404, "ROUTE_REQUEST_NOT_FOUND", "경로 요청을 찾을 수 없어요.")
        if not secrets.compare_digest(access_token.encode(), record.access_token.encode()):
            raise ApiError(403, "FORBIDDEN", "이 경로를 조회할 수 없는 토큰입니다.")
        return self._status_payload(record)

    def _now(self) -> datetime:
        return as_kst(self._clock())

    def _register(self, direction: RouteDirection, request: RouteRequest, body: str) -> _RouteRecord:
        route_id = _random_id("rr_", 16)
        while route_id in self._records:
            route_id = _random_id("rr_", 16)
        record = self._new_record(direction, request, body, route_id, _random_id("rrt_", 24))
        self._records[route_id] = record
        self._request_keys[record.request_key] = record
        record.task = asyncio.create_task(self._process(record))
        return record

    def _new_record(
        self, direction: RouteDirection, request: RouteRequest, body: str, route_id: str, token: str,
    ) -> _RouteRecord:
        started = asyncio.get_running_loop().time()
        now = self._now()
        return _RouteRecord(
            route_id=route_id,
            access_token=token,
            direction=direction,
            request=request,
            body=body,
            depart_at=now,
            updated_at=now,
            sync_deadline=started + _SYNC_WAIT_S,
            deadline=started + _REQUEST_LIMIT_S,
        )

    async def _create_db_route(
        self, direction: RouteDirection, request: RouteRequest, body: str,
    ) -> tuple[int, dict[str, object]]:
        assert self._store is not None
        request_id = self._private_hash("request-id", f"{direction}:{request.request_id}")
        body_hash = self._private_hash("request-body", body)
        existing = await asyncio.to_thread(self._store.request_for_retry, request_id, body_hash)
        if existing is not None:
            return await asyncio.to_thread(self._replay, direction, existing)

        festival = await asyncio.to_thread(find_festival, request.festival_id)
        self._validate_festival(request, festival)
        assert festival is not None
        route_id = _random_id("rr_", 16)
        record = self._new_record(direction, request, body, route_id, self._db_token(route_id))
        record.festival = festival
        origin_type, origin_hash = self._place_fields(request.origin)
        destination_type, destination_hash = self._place_fields(request.destination)
        created = await asyncio.to_thread(self._store.register, {
            "route_id": route_id, "request_id": request_id, "body_hash": body_hash,
            "token_hash": token_hash(record.access_token), "direction": direction,
            "festival_id": festival.festival_id, "festival_lat": festival.lat, "festival_lng": festival.lng,
            "origin_type": origin_type, "origin_hash": origin_hash,
            "destination_type": destination_type, "destination_hash": destination_hash,
            "travel_mode": request.travel_mode, "route_preference": request.route_preference,
            "constraints": request.user_constraints.model_dump_json(),
            "route_key": self._private_hash("pending-route", route_id), "now": record.depart_at,
        })
        if not created:
            existing = await asyncio.to_thread(self._store.request_for_retry, request_id, body_hash)
            assert existing is not None
            return await asyncio.to_thread(self._replay, direction, existing)
        record.task = asyncio.create_task(self._process(record))
        return await self._submit_registered(record)

    def _private_hash(self, purpose: str, value: str) -> str:
        return hmac.digest(self._secret, f"{purpose}:{value}".encode(), "sha256").hex()

    def _db_token(self, route_id: str) -> str:
        digest = bytes.fromhex(self._private_hash("route-token", route_id))
        return "rrt_" + b32encode(digest).decode()[:24]

    def _place_fields(self, endpoint: Endpoint) -> tuple[str, str | None]:
        if isinstance(endpoint, FestivalEndpoint):
            return "festival", None
        value = (
            f"query:{' '.join(endpoint.query.casefold().split())}"
            if endpoint.query is not None else f"point:{endpoint.lat:.6f},{endpoint.lng:.6f}"
        )
        return "user", self._private_hash("place", value)

    async def _process(self, record: _RouteRecord) -> ProviderResult | None:
        try:
            async with asyncio.timeout_at(record.deadline):
                if self._store is not None:
                    await asyncio.to_thread(self._store.start, record.route_id, self._now())
                query = await self._resolve_query(record)
                result = await self._find_route(record, query)
        except TimeoutError:
            result = _TIMEOUT
        except ApiError as error:
            result = _Failure(error.code, error.message, error.retryable, http_status=error.status)
        except ProviderError as error:
            result = _PROVIDER_FAILURES.get(error.kind, _UPSTREAM_ERROR)
        except Exception:
            result = _UPSTREAM_ERROR

        if self._store is not None:
            try:
                await asyncio.to_thread(self._persist_result, record, result)
            except ApiError:
                result = _DB_UNAVAILABLE

        # 카카오 본문은 대기 중인 접수 응답에만 넘긴다.
        record.accepted |= asyncio.get_running_loop().time() >= record.sync_deadline
        record.updated_at = self._now()
        record.task = None
        if isinstance(result, _CachedRoute):
            record.cached = result
        elif isinstance(result, ProviderResult):
            record.failure = _SECONDARY_ONLY
            if not record.accepted:
                return result
        else:
            record.failure = result
            if self._store is None and result.http_status != 200 and not record.accepted:
                del self._records[record.route_id]
                del self._request_keys[record.request_key]
        return None

    async def _resolve_query(self, record: _RouteRecord) -> RouteQuery:
        request = record.request
        festival = record.festival
        if festival is None:
            festival = await asyncio.to_thread(find_festival, request.festival_id)
        self._validate_festival(request, festival)
        assert festival is not None
        record.festival = festival
        origin = await self._coordinates(request.origin, festival)
        destination = await self._coordinates(request.destination, festival)
        return RouteQuery(origin, destination, record.depart_at)

    @staticmethod
    def _validate_festival(request: RouteRequest, festival: FestivalDetail | None) -> None:
        if festival is None:
            raise ApiError(404, "FESTIVAL_NOT_FOUND", "축제를 찾을 수 없어요.")
        uses_festival = any(
            isinstance(endpoint, FestivalEndpoint) for endpoint in (request.origin, request.destination)
        )
        if uses_festival and (festival.lat is None or festival.lng is None):
            raise ApiError(400, "FESTIVAL_LOCATION_UNKNOWN", "축제 장소의 좌표를 알 수 없어요.")

    async def _coordinates(self, endpoint: Endpoint, festival: FestivalDetail) -> Coordinates:
        if isinstance(endpoint, FestivalEndpoint):
            assert festival.lat is not None and festival.lng is not None
            return festival.lat, festival.lng
        if endpoint.query is None:
            assert endpoint.lat is not None and endpoint.lng is not None
            return endpoint.lat, endpoint.lng
        try:
            lat, lng, _ = await asyncio.to_thread(self._search_place, endpoint.query)
        except ProviderError as error:
            if error.kind in ("no_result", "bad_request"):
                raise ApiError(400, "ROUTE_INVALID", "목적지를 찾을 수 없어요") from None
            raise
        return lat, lng

    def _search_place(self, query: str) -> tuple[float, float, str]:
        if not self._quota.try_acquire("kakao_local"):
            raise ProviderError("quota", "kakao")
        return self._kakao().search_place(query)

    def _route_key(self, record: _RouteRecord, query: RouteQuery) -> str:
        start_lat, start_lng = query.origin
        end_lat, end_lng = query.destination
        parts = (
            record.direction, f"{start_lat:.4f},{start_lng:.4f}", f"{end_lat:.4f},{end_lng:.4f}",
            record.request.travel_mode, record.request.route_preference,
            str(int(record.depart_at.timestamp()) // 300),
        )
        return hmac.digest(self._secret, "|".join(parts).encode(), "sha256").hex()

    async def _find_route(self, record: _RouteRecord, query: RouteQuery) -> _FlightResult:
        key = self._route_key(record, query)
        record.route_key = key
        cached = self._cache.get(key)
        if cached is not None and self._live_result(cached) is not None:
            record.source_type = "cache"
            return cached
        flight = self._flights.get(key)
        if flight is None:
            flight = asyncio.create_task(self._fetch(key, query, record.sync_deadline))
            self._flights[key] = flight
        else:
            record.source_type = "shared"
        return await asyncio.shield(flight)

    async def _fetch(self, key: str, query: RouteQuery, sync_deadline: float) -> _FlightResult:
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + _FLIGHT_LIMIT_S
            async with asyncio.timeout_at(deadline):
                try:
                    result = await asyncio.to_thread(
                        self._query_provider, "tmap", query, deadline, loop.time,
                    )
                except ProviderError as error:
                    return await self._fallback(query, error.kind, sync_deadline)
                return self._cache_result(key, result)
        except TimeoutError:
            return _TIMEOUT
        except Exception:
            return _UPSTREAM_ERROR
        finally:
            del self._flights[key]

    async def _fallback(
        self, query: RouteQuery, primary_error: ErrorKind, sync_deadline: float
    ) -> ProviderResult | _Failure:
        if primary_error in ("too_close", "bad_request", "service_ended"):
            return _PROVIDER_FAILURES[primary_error]
        loop = asyncio.get_running_loop()
        if loop.time() >= sync_deadline:
            return _SECONDARY_ONLY
        try:
            async with asyncio.timeout_at(sync_deadline):
                return await asyncio.to_thread(
                    self._query_provider, "kakao", query, sync_deadline, loop.time,
                )
        except TimeoutError:
            return _SECONDARY_ONLY
        except ProviderError as error:
            if primary_error == error.kind == "quota":
                return _QUOTA_EXCEEDED
            kind = primary_error if error.kind == "quota" else error.kind
            return _PROVIDER_FAILURES.get(kind, _UPSTREAM_ERROR)

    def _query_provider(
        self, name: ProviderName, query: RouteQuery, deadline: float, clock: Callable[[], float]
    ) -> ProviderResult:
        if clock() >= deadline:
            raise TimeoutError
        if not self._quota.try_acquire(name):
            raise ProviderError("quota", name)
        if clock() >= deadline:
            raise TimeoutError
        provider = self._tmap() if name == "tmap" else self._kakao()
        return provider.query(query)

    def _cache_result(self, key: str, result: ProviderResult) -> _CachedRoute:
        cached = _CachedRoute(key, self._now() + timedelta(seconds=_CACHE_TTL_S), result)
        self._cache[key] = cached
        asyncio.get_running_loop().call_later(_CACHE_TTL_S, self._expire_cache, cached)
        return cached

    def _expire_cache(self, cached: _CachedRoute) -> None:
        cached.result = None
        if self._cache.get(cached.key) is cached:
            del self._cache[cached.key]

    def _live_result(self, cached: _CachedRoute) -> ProviderResult | None:
        if self._now() >= cached.valid_until:
            self._expire_cache(cached)
        return cached.result

    def _record_result(self, record: _RouteRecord) -> ProviderResult | None:
        if record.cached is None:
            return None
        result = self._live_result(record.cached)
        if result is None:
            record.cached = None
            record.failure = _RESULT_EXPIRED
            record.updated_at = self._now()
        return result

    def _persist_result(self, record: _RouteRecord, outcome: _FlightResult) -> None:
        assert self._store is not None
        now = self._now()
        result = outcome.result if isinstance(outcome, _CachedRoute) else None
        if result is not None:
            candidates = json.dumps(stored_candidates(result), ensure_ascii=False, sort_keys=True)
            self._store.finish(
                record.route_id, now, record.route_key, status="ready", error_code=None,
                error_detail=None, result={
                    "queried_at": datetime.fromisoformat(result.queried_at),
                    "candidates": candidates,
                    "evidence": json.dumps({"notices": result.notices}, ensure_ascii=False),
                    "route_hash": self._private_hash("result", candidates),
                    "source_type": record.source_type,
                    "validity_check": json.dumps({"route_key_matched": True})
                    if record.source_type == "cache" else None,
                },
            )
            return
        if isinstance(outcome, _Failure):
            failure = outcome
        elif isinstance(outcome, ProviderResult):
            failure = _SECONDARY_ONLY
        else:
            failure = _DB_RESULT_EXPIRED
        self._store.finish(
            record.route_id, now, record.route_key, status=failure.status,
            error_code=failure.code, error_detail=asdict(failure), result=None,
        )

    def _replay(self, direction: RouteDirection, route_id: str) -> tuple[int, dict[str, object]]:
        token = self._db_token(route_id)
        try:
            failure, payload = self._db_status(direction, route_id, token)
        except ApiError as error:
            if error.status != 401:
                raise
            # 접수 요청의 멱등 키는 조회 권한이 만료된 뒤에도 기존 요청을 가리킨다.
            return 200, self._state_payload(route_id, "unavailable", self._now(), _ACCESS_EXPIRED)
        if failure is not None and failure.http_status != 200:
            raise ApiError(failure.http_status, failure.code, failure.message, failure.retryable)
        payload["route_access_token"] = token
        if payload["route_status"] in ("queued", "processing"):
            payload["status_url"] = f"/api/v1/routes/{direction}/{route_id}"
            return 202, payload
        return 200, payload

    def _db_status(
        self, direction: RouteDirection, route_id: str, token: str,
    ) -> tuple[_Failure | None, dict[str, object]]:
        assert self._store is not None
        now = self._now()
        request, result = self._store.lookup(direction, route_id, token, now)
        status = request["status"]
        updated_at = request["completed_at"] or request["started_at"] or request["submitted_at"]
        failure = _Failure(**request["error_detail"]) if request["error_detail"] else None
        if status == "ready" and result is None:
            # 백업 복원 등으로 결과가 빠진 요청은 완료 경로로 표시하지 않는다.
            failure = _DB_RESULT_EXPIRED
        if result is not None and result["purged_at"] is not None:
            failure = _DB_RESULT_EXPIRED
            updated_at = result["purged_at"]
        if status in ("queued", "processing") and now >= request["submitted_at"] + timedelta(seconds=_REQUEST_LIMIT_S):
            failure = _TIMEOUT
            updated_at = request["submitted_at"] + timedelta(seconds=_REQUEST_LIMIT_S)

        payload = self._state_payload(route_id, status, updated_at, failure)
        if result is not None and failure is None:
            # 새 프로세스도 민감한 요청 원문 없이 저장된 경로 요약을 응답할 수 있다.
            payload.update({
                "direction": direction, "festival_id": request["festival_id"],
                "origin": self._stored_endpoint(request["origin_type"], request),
                "destination": self._stored_endpoint(request["destination_type"], request),
                "travel_mode": request["travel_mode"], "route_preference": request["route_preference"],
                "route_candidates": result["candidates"], "provider": "tmap", "provider_tier": "primary",
                "queried_at": as_kst(result["queried_at"]).isoformat(),
                "verification_status": "control_unverified",
                "constraint_status": self._constraint_status(request["constraints"]),
                "coverage": {"scope": "national", "supported": True}, "score_version": None,
                "notices": [_CONTROL_NOTICE, *result["evidence"].get("notices", [])],
            })
        return failure, payload

    @staticmethod
    def _stored_endpoint(kind: str, request: RowMapping) -> dict[str, object]:
        if kind == "festival":
            return {"type": "festival", "lat": float(request["festival_lat"]), "lng": float(request["festival_lng"])}
        return {"type": "place"}

    def _accepted_payload(self, record: _RouteRecord) -> dict[str, object]:
        return {
            "route_request_id": record.route_id,
            "route_status": "queued",
            "status_url": f"/api/v1/routes/{record.direction}/{record.route_id}",
            "route_access_token": record.access_token,
            "retry_after_s": _RETRY_AFTER_S,
            "is_mock": False,
        }

    def _status_payload(self, record: _RouteRecord) -> dict[str, object]:
        result = self._record_result(record)
        failure = record.failure
        status = "ready" if result is not None else "processing"
        body = self._state_payload(record.route_id, status, record.updated_at, failure)
        if result is not None:
            body.update(self._ready_payload(record, result))
        return body

    @staticmethod
    def _state_payload(
        route_id: str, status: str, updated_at: datetime, failure: _Failure | None,
    ) -> dict[str, object]:
        if failure is not None:
            status = failure.status
        body: dict[str, object] = {
            "route_request_id": route_id,
            "route_status": status,
            "completed_valid_route": status == "ready",
            "updated_at": as_kst(updated_at).isoformat(),
            "is_mock": False,
        }
        if failure is not None:
            body["error"] = {"code": failure.code, "message": failure.message, "retryable": failure.retryable}
            body["notices"] = [failure.message, *failure.notices]
        elif status in ("queued", "processing"):
            body["retry_after_s"] = _RETRY_AFTER_S
        return body

    def _ready_payload(self, record: _RouteRecord, result: ProviderResult) -> dict[str, object]:
        request, festival = record.request, record.festival
        assert festival is not None
        return {
            "route_request_id": record.route_id,
            "route_status": "ready",
            "route_access_token": record.access_token,
            "direction": record.direction,
            "festival_id": festival.festival_id,
            "origin": _format_endpoint(request.origin, festival),
            "destination": _format_endpoint(request.destination, festival),
            "travel_mode": request.travel_mode,
            "route_preference": request.route_preference,
            "route_candidates": result.candidates,
            "provider": result.provider,
            "provider_tier": result.provider_tier,
            "queried_at": result.queried_at,
            "verification_status": "control_unverified",
            "completed_valid_route": True,
            "constraint_status": self._constraint_status(request.user_constraints.model_dump()),
            "coverage": {"scope": "national", "region_code": festival.region_code, "supported": True},
            "score_version": None,
            "notices": [_CONTROL_NOTICE, *result.notices],
            "is_mock": False,
        }

    @staticmethod
    def _constraint_status(constraints: dict[str, object]) -> dict[str, str]:
        status = {"control": "unverified"}
        for name in ("with_child", "wheelchair"):
            if constraints.get(name):
                status[name] = "not_verifiable"
        if constraints.get("max_walk_m") is not None:
            status["max_walk_m"] = "not_verifiable"
        return status


@lru_cache(maxsize=1)
def get_service() -> RealRouteService:
    mode = os.environ.get("ROUTE_STORE", "memory")
    if mode not in ("memory", "db"):
        raise ApiError(503, "ROUTE_STORE_UNAVAILABLE", "귀가 저장소 설정을 확인해 주세요.", True)
    return RealRouteService(store=RouteStore() if mode == "db" else None)
