"""A04·A05용 PostgreSQL 요청·결과 저장소."""

import hashlib
import hmac
import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import RowMapping, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.errors import ApiError
from api.providers.route_base import ProviderResult
from api.schemas.routes import RouteDirection
from shared.db.session import service_db_session

TOKEN_TTL = timedelta(minutes=10)
RESULT_TTL = timedelta(hours=24)
DEFAULT_PURGE_AFTER_HOURS = 23

_STATUS = """
    SELECT route_request_id, direction, festival_id, festival_lat, festival_lng, origin_type,
           destination_type, travel_mode, route_preference, constraints, status, error_code,
           error_detail, submitted_at, started_at, completed_at, access_token_hash
      FROM public.route_requests
     WHERE route_request_id = :route_id AND direction = :direction AND request_body_hash IS NOT NULL
"""
_EXPIRED_RESULTS = """
    WHERE provider = 'tmap' AND purged_at IS NULL AND queried_at <= :cutoff
"""
# A05와 정리 명령이 공유한다. 013 트리거가 같은 트랜잭션에서 삭제 시각을 요청 행에 기록한다.
_PURGE = """
    UPDATE public.route_results
       SET candidates = NULL, evidence = '{}', provider_ref = NULL,
           validity_check = CASE WHEN source_type IN ('cache','alternate') THEN '{}'::jsonb END,
           purged_at = :now
""" + _EXPIRED_RESULTS
_COUNT_EXPIRED = text("SELECT count(*) FROM public.route_results " + _EXPIRED_RESULTS)
_PURGE_LOCK = text("SELECT pg_try_advisory_xact_lock(hashtext('noldaga.purge_route_results'))")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def stored_candidates(result: ProviderResult) -> list[dict[str, Any]]:
    """TMAP 후보의 경로선·정류장 좌표를 제외한 안내 필드만 저장한다."""
    if result.provider != "tmap":
        raise ValueError("TMAP 후보만 저장할 수 있습니다.")
    candidates = []
    for source in result.candidates:
        candidate = {
            key: source[key] for key in (
                "candidate_id", "summary", "duration_min", "distance_m", "walk_m",
                "transfers", "fare_krw", "service_running", "score",
            ) if key in source
        }
        candidate["legs"] = []
        for leg in source.get("legs", []):
            summary = {
                key: leg[key] for key in ("mode", "duration_min", "line", "distance_m") if key in leg
            }
            if "stops" in leg:
                summary["stops"] = [
                    {key: stop[key] for key in ("id", "name") if key in stop} for stop in leg["stops"]
                ]
            candidate["legs"].append(summary)
        candidate["area_evidence"] = {"crowd_areas": [], "traffic_incidents": []}
        candidate["mode_evidence"] = {
            "bus_crowding": {"status": "unverified", "reason": "버스 혼잡 연결 전"},
        }
        candidates.append(candidate)
    return candidates


class RouteStore:
    def __init__(
        self, session: Callable[[], AbstractContextManager[Session]] = service_db_session,
    ) -> None:
        self._session = session

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            with self._session() as session:
                yield session
        except (SQLAlchemyError, ValueError):
            raise ApiError(503, "ROUTE_STORE_UNAVAILABLE", "귀가 요청 저장소에 연결할 수 없어요.", True) from None

    def register(self, values: dict[str, Any]) -> bool:
        with self._transaction() as session:
            created = session.execute(text("""
                INSERT INTO public.route_requests (
                    route_request_id, request_id, request_body_hash, access_token_hash,
                    direction, festival_id, festival_lat, festival_lng, origin_type, destination_type,
                    origin_place_hash, destination_place_hash, travel_mode, route_preference,
                    constraints, route_key, status, submitted_at, created_at, is_mock
                ) VALUES (
                    :route_id, :request_id, :body_hash, :token_hash, :direction, :festival_id,
                    :festival_lat, :festival_lng, :origin_type, :destination_type,
                    :origin_hash, :destination_hash, :travel_mode, :route_preference,
                    CAST(:constraints AS jsonb), :route_key, 'queued', :now, :now, false
                )
                ON CONFLICT (request_id) DO NOTHING
                RETURNING route_request_id
            """), values).scalar_one_or_none()
            return created is not None

    def request_for_retry(self, request_id: str, body_hash: str) -> str | None:
        with self._transaction() as session:
            row = session.execute(text("""
                SELECT route_request_id, request_body_hash FROM public.route_requests
                WHERE request_id = :request_id
            """), {"request_id": request_id}).one_or_none()
        if row is None:
            return None
        if row.request_body_hash is None or not hmac.compare_digest(row.request_body_hash, body_hash):
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "이미 다른 본문에 사용한 요청 ID입니다.")
        return row.route_request_id

    def start(self, route_id: str, now: datetime) -> None:
        with self._transaction() as session:
            session.execute(text("""
                UPDATE public.route_requests SET status = 'processing', started_at = :now
                WHERE route_request_id = :route_id AND status = 'queued'
            """), {"route_id": route_id, "now": now})

    def finish(
        self, route_id: str, now: datetime, route_key: str | None, *,
        status: str, error_code: str | None, error_detail: dict[str, Any] | None,
        result: dict[str, Any] | None,
    ) -> None:
        with self._transaction() as session:
            session.execute(text("""
                UPDATE public.route_requests
                   SET status = :status, completed_at = :now, error_code = :error_code,
                       error_detail = CAST(:error_detail AS jsonb), route_key = COALESCE(:route_key, route_key)
                 WHERE route_request_id = :route_id
            """), {
                "status": status, "now": now, "error_code": error_code, "route_key": route_key,
                "error_detail": json.dumps(error_detail) if error_detail else None, "route_id": route_id,
            })
            if result is not None:
                session.execute(text("""
                    INSERT INTO public.route_results (
                        route_request_id, provider, provider_tier, queried_at, candidates, evidence,
                        route_hash, source_type, validity_check, validation_status, is_mock
                    ) VALUES (
                        :route_id, 'tmap', 'primary', :queried_at, CAST(:candidates AS jsonb),
                        CAST(:evidence AS jsonb), :route_hash, :source_type, CAST(:validity_check AS jsonb),
                        'control_unverified', false
                    )
                """), {**result, "route_id": route_id})

    def lookup(
        self, direction: RouteDirection, route_id: str, token: str, now: datetime,
    ) -> tuple[RowMapping, RowMapping | None]:
        with self._transaction() as session:
            params = {"route_id": route_id, "direction": direction}
            request = session.execute(text(_STATUS), params).mappings().one_or_none()
            if request is None:
                raise ApiError(404, "ROUTE_REQUEST_NOT_FOUND", "경로 요청을 찾을 수 없어요.")
            if not hmac.compare_digest(request["access_token_hash"], token_hash(token)):
                raise ApiError(403, "FORBIDDEN", "이 경로를 조회할 수 없는 토큰입니다.")
            if now >= request["submitted_at"] + TOKEN_TTL:
                raise ApiError(401, "UNAUTHORIZED", "경로 조회 토큰이 만료됐어요. 새로 요청해 주세요.")
            if request["status"] != "ready":
                return request, None

            session.execute(
                text(_PURGE + " AND route_request_id = :route_id"),
                {"now": now, "cutoff": now - RESULT_TTL, "route_id": route_id},
            )
            result = session.execute(text("""
                SELECT queried_at, candidates, evidence, purged_at
                FROM public.route_results WHERE route_request_id = :route_id AND provider = 'tmap'
            """), params).mappings().one_or_none()
            return request, result

    def purge_expired(
        self, now: datetime, *, after_hours: int = DEFAULT_PURGE_AFTER_HOURS, dry_run: bool = False,
    ) -> int | None:
        """정리 기준에 도달한 결과 수를 반환한다. 다른 정리 작업이 실행 중이면 None이다."""
        with self._transaction() as session:
            if not session.execute(_PURGE_LOCK).scalar_one():
                return None
            params = {"cutoff": now - timedelta(hours=after_hours)}
            if dry_run:
                return session.execute(_COUNT_EXPIRED, params).scalar_one()
            return session.execute(text(_PURGE), {**params, "now": now}).rowcount
