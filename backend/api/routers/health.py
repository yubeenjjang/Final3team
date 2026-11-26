import os

from anyio import fail_after
from fastapi import APIRouter, Request, Response
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.auth.tokens import uses_auth_db
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.common import HealthResponse
from api.services.real_festival_info import uses_real_info
from api.services.real_routes import uses_real_routes
from shared.db.session import user_db_session
from shared import redis as redis_connection

router = APIRouter()
_DB_TIMEOUT_SECONDS = 1


def uses_health_db() -> bool:
    return (
        uses_festival_db()
        or uses_auth_db()
        or (uses_real_routes() and os.environ.get("ROUTE_STORE") == "db")
        or uses_real_info("notices")
        or uses_real_info("transit")
        or (uses_real_info("visit-forecast") and os.environ.get("VISIT_FORECAST_STORE") == "db")
    )


async def _check_db() -> None:
    async with user_db_session(user_id=None) as db:
        await db.execute(text(f"SET LOCAL statement_timeout = {_DB_TIMEOUT_SECONDS * 1000}"))
        await db.execute(text("SELECT 1"))


@router.get("/health", responses={503: {"model": HealthResponse}})
async def get_health(request: Request, response: Response) -> HealthResponse:
    version = request.app.version
    db_enabled = uses_health_db()
    redis_enabled = redis_connection.configured_url() is not None
    if not db_enabled and not redis_enabled:
        return HealthResponse(version=version)

    db_status = "mock"
    if db_enabled:
        try:
            # Repeated cancellation also interrupts psycopg's query cancellation wait.
            with fail_after(_DB_TIMEOUT_SECONDS):
                await _check_db()
            db_status = "ok"
        except (SQLAlchemyError, OSError, RuntimeError, ValueError, TimeoutError):
            db_status = "unavailable"

    redis_status = "not_configured"
    if redis_enabled:
        try:
            with fail_after(1):
                redis_status = "ok" if await redis_connection.ping() else "unavailable"
        except (RedisError, OSError, RuntimeError, ValueError, TimeoutError):
            redis_status = "unavailable"

    if db_status == "unavailable" or redis_status == "unavailable":
        response.status_code = 503
    return HealthResponse(
        status="degraded" if response.status_code == 503 else "ok",
        db=db_status, redis=redis_status, version=version, is_mock=False,
    )
