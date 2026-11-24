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
from sqlalchemy.exc import TimeoutError as DBPoolTimeout

from api.errors import SERVICE_BUSY_CODE, SERVICE_BUSY_MESSAGE, ApiError
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
_DB_RESULT_EXPIRED = replace(
    _RESULT_EXPIRED, message="경로 보관 시간이 지났어요. 새 경로를 다시 요청해 주세요.", retryable=False,
)
_ACCESS_EXPIRED = _Failure("ROUTE_ACCESS_EXPIRED", "경로 조회 시간이 지났어요. 새 요청 ID로 다시 요청해 주세요.")
_DB_UNAVAILABLE = _Failure(
    "ROUTE_STORE_UNAVAILABLE", "귀가 요청 저장소에 연결할 수 없어요.", True, http_status=503,
)
_DB_BUSY = _Failure(SERVICE_BUSY_CODE, SERVICE_BUSY_MESSAGE, True, http_status=503)
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
    request_keys: set[str] = field(default_factory=set, repr=False)


@dataclass
class _RouteRecord:
    route_id: str
    access_token: str = field(repr=False)
    direction: RouteDirection
    request: RouteRequest | None = field(repr=False)
    request_key: str = field(repr=False)
    body_hash: str = field(repr=False)
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


_RouteOutcome = _CachedRoute | ProviderResult | _Failure
_PrimaryResult = _CachedRoute | _Failure | ErrorKind


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
        control_version: str | None = None,
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
        self._control_version = control_version or "none"
        self._records: dict[str, _RouteRecord] = {}
        self._request_keys: dict[str, _RouteRecord] = {}
        self._cache: dict[str, _CachedRoute] = {}
        self._flights: dict[str, asyncio.Task[_PrimaryResult]] = {}

    async def create_route(
        self, direction: RouteDirection, request: RouteRequest, body: dict[str, object]
    ) -> tuple[int, dict[str, object]]:
        request_key = self._private_hash("request-id", f"{direction}:{request.request_id}")
        body_hash = self._private_hash("request-body", json.dumps(body, sort_keys=True))
        if self._store is not None:
            return await self._create_db_route(direction, request, request_key, body_hash)

        record = self._request_keys.get(request_key)
        if record is None:
            record = self._register(direction, request, request_key, body_hash)
        elif not hmac.compare_digest(record.body_hash, body_hash):
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")
        return await self._submit_registered(record, request)

    async def _submit_registered(
        self, record: _RouteRecord, request: RouteRequest,
    ) -> tuple[int, dict[str, object]]:
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
            return 200, self._ready_payload(record, request, result)
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

    def _register(
        self, direction: RouteDirection, request: RouteRequest, request_key: str, body_hash: str,
    ) -> _RouteRecord:
        route_id = _random_id("rr_", 16)
        while route_id in self._records:
            route_id = _random_id("rr_", 16)
        record = self._new_record(direction, request, request_key, body_hash, route_id, _random_id("rrt_", 24))
        self._records[route_id] = record
        self._request_keys[record.request_key] = record
        record.task = asyncio.create_task(self._process(record))
        return record

    def _new_record(
        self, direction: RouteDirection, request: RouteRequest, request_key: str, body_hash: str,
        route_id: str, token: str,
    ) -> _RouteRecord:
        started = asyncio.get_running_loop().time()
        now = self._now()
        return _RouteRecord(
            route_id=route_id,
            access_token=token,
            direction=direction,
            request=request,
            request_key=request_key,
            body_hash=body_hash,
            depart_at=now,
            updated_at=now,
            sync_deadline=started + _SYNC_WAIT_S,
            deadline=started + _REQUEST_LIMIT_S,
        )

    async def _create_db_route(
        self, direction: RouteDirection, request: RouteRequest, request_key: str, body_hash: str,
    ) -> tuple[int, dict[str, object]]:
        assert self._store is not None
        existing = await asyncio.to_thread(self._store.request_for_retry, request_key, body_hash)
        if existing is not None:
            return await asyncio.to_thread(self._replay, direction, existing)

        festival = await asyncio.to_thread(find_festival, request.festival_id)
        self._validate_festival(request, festival)
        assert festival is not None
        route_id = _random_id("rr_", 16)
        record = self._new_record(direction, request, request_key, body_hash, route_id, self._db_token(route_id))
        record.festival = festival
        origin_type, origin_hash = self._place_fields(request.origin)
        destination_type, destination_hash = self._place_fields(request.destination)
        created = await asyncio.to_thread(self._store.register, {
            "route_id": route_id, "request_id": request_key, "body_hash": body_hash,
            "token_hash": token_hash(record.access_token), "direction": direction,
            "festival_id": festival.festival_id, "festival_lat": festival.lat, "festival_lng": festival.lng,
            "origin_type": origin_type, "origin_hash": origin_hash,
            "destination_type": destination_type, "destination_hash": destination_hash,
            "travel_mode": request.travel_mode, "route_preference": request.route_preference,
            "constraints": request.user_constraints.model_dump_json(),
            "route_key": "pending:" + self._private_hash("pending-route", route_id),
            "now": record.depart_at,
        })
        if not created:
            existing = await asyncio.to_thread(self._store.request_for_retry, request_key, body_hash)
            assert existing is not None
            return await asyncio.to_thread(self._replay, direction, existing)
        record.task = asyncio.create_task(self._process(record))
        return await self._submit_registered(record, request)

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
        except DBPoolTimeout:
            result = _DB_BUSY
        except ApiError as error:
            result = _Failure(error.code, error.message, error.retryable, http_status=error.status)
        except ProviderError as error:
            result = _PROVIDER_FAILURES.get(error.kind, _UPSTREAM_ERROR)
        except Exception:
            result = _UPSTREAM_ERROR

        if self._store is not None:
            try:
                await asyncio.to_thread(self._persist_result, record, result)
            except DBPoolTimeout:
                result = _DB_BUSY
            except ApiError:
                result = _DB_UNAVAILABLE

        # 카카오 본문은 대기 중인 접수 응답에만 넘긴다.
        record.accepted |= asyncio.get_running_loop().time() >= record.sync_deadline
        record.updated_at = self._now()
        record.task = None
        # 메모리 모드에서는 A05의 유효한 TMAP 응답을 만드는 동안만 원문을 보관한다.
        if isinstance(result, _CachedRoute):
            record.cached = result
            if self._store is None and result.result is not None:
                result.request_keys.add(record.request_key)
            else:
                record.request = None
            return None
        record.request = None
        if isinstance(result, ProviderResult):
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
        assert request is not None
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

    def _route_key(self, record: _RouteRecord, query: RouteQuery, provider: ProviderName) -> str:
        request = record.request
        assert request is not None
        conditions = {
            "direction": record.direction,
            "festival_id": request.festival_id,
            "origin_type": request.origin.type,
            "destination_type": request.destination.type,
            "origin": [f"{value:.4f}" for value in query.origin],
            "destination": [f"{value:.4f}" for value in query.destination],
            "travel_mode": request.travel_mode,
            "route_preference": request.route_preference,
            "user_constraints": request.user_constraints.model_dump(),
            "departure": request.departure,
            "departure_bucket": int(record.depart_at.timestamp()) // 300,
            "control_version": self._control_version,
            "provider": provider,
        }
        normalized = json.dumps(conditions, sort_keys=True, separators=(",", ":"))
        return "v2:" + self._private_hash("route-key-v2", normalized)

    async def _find_route(self, record: _RouteRecord, query: RouteQuery) -> _RouteOutcome:
        key = self._route_key(record, query, "tmap")
        record.route_key = key
        cached = self._cache.get(key)
        if cached is not None and self._live_result(cached) is not None:
            record.source_type = "cache"
            return cached
        flight = self._flights.get(key)
        if flight is None:
            flight = asyncio.create_task(self._fetch_tmap(key, query))
            self._flights[key] = flight
        else:
            record.source_type = "shared"
        outcome = await asyncio.shield(flight)
        if isinstance(outcome, str):
            return await self._fallback(record, query, outcome)
        return outcome

    async def _fetch_tmap(self, key: str, query: RouteQuery) -> _PrimaryResult:
        try:
            loop = asyncio.get_running_loop()
            deadline = loop.time() + _FLIGHT_LIMIT_S
            async with asyncio.timeout_at(deadline):
                result = await asyncio.to_thread(
                    self._query_provider, "tmap", query, deadline, loop.time,
                )
                return self._cache_result(key, result)
        except ProviderError as error:
            return error.kind
        except TimeoutError:
            return _TIMEOUT
        except Exception:
            return _UPSTREAM_ERROR
        finally:
            del self._flights[key]

    async def _fallback(
        self, record: _RouteRecord, query: RouteQuery, primary_error: ErrorKind,
    ) -> ProviderResult | _Failure:
        if primary_error in ("too_close", "bad_request", "service_ended"):
            return _PROVIDER_FAILURES[primary_error]
        loop = asyncio.get_running_loop()
        sync_deadline = record.sync_deadline
        if loop.time() >= sync_deadline:
            return _SECONDARY_ONLY
        # 카카오 결과는 각 요청의 동기 응답에서만 제공한다.
        record.route_key = self._route_key(record, query, "kakao")
        record.source_type = "fresh"
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
        for request_key in cached.request_keys:
            self._request_keys[request_key].request = None
        cached.request_keys.clear()
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

    def _persist_result(self, record: _RouteRecord, outcome: _RouteOutcome) -> None:
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
            assert record.request is not None
            body.update(self._ready_payload(record, record.request, result))
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

    def _ready_payload(
        self, record: _RouteRecord, request: RouteRequest, result: ProviderResult,
    ) -> dict[str, object]:
        festival = record.festival
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
