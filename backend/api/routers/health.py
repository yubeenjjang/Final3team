import os

from anyio import fail_after
from fastapi import APIRouter, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.auth.tokens import uses_auth_db
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.common import HealthResponse
from api.services.real_festival_info import uses_real_info
from api.services.real_routes import uses_real_routes
from shared.db.session import user_db_session

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


async def db_is_ready() -> bool:
    try:
        # Repeated cancellation also interrupts psycopg's query cancellation wait.
        with fail_after(_DB_TIMEOUT_SECONDS):
            async with user_db_session(user_id=None) as db:
                await db.execute(text(f"SET LOCAL statement_timeout = {_DB_TIMEOUT_SECONDS * 1000}"))
                await db.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, RuntimeError, ValueError):
        return False
    return True


@router.get("/health", responses={503: {"model": HealthResponse}})
async def get_health(request: Request, response: Response) -> HealthResponse:
    version = request.app.version
    if not uses_health_db():
        return HealthResponse(version=version)

    if not await db_is_ready():
        response.status_code = 503
        return HealthResponse(
            status="degraded", db="unavailable", redis="not_configured",
            version=version, is_mock=False,
        )
    return HealthResponse(db="ok", redis="not_configured", version=version, is_mock=False)
