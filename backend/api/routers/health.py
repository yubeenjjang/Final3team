import os

from anyio import fail_after
from dotenv import dotenv_values, find_dotenv
from fastapi import APIRouter, Request, Response
from psycopg import AsyncConnection, Error as PostgresError

from api.auth.tokens import uses_auth_db
from api.routers.festivals.catalog import uses_festival_db
from api.schemas.common import HealthResponse
from api.services.festival_store import get_app_db_url
from api.services.real_festival_info import uses_real_info
from api.services.real_routes import uses_real_routes

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
    dotenv = {
        name: value for name, value in dotenv_values(find_dotenv(usecwd=True)).items()
        if value is not None
    }
    url = get_app_db_url(dotenv | os.environ)
    connection = await AsyncConnection.connect(
        host=url.host,
        port=url.port,
        dbname=url.database,
        user=url.username,
        password=url.password,
        autocommit=True,
        options=f"-c statement_timeout={_DB_TIMEOUT_SECONDS * 1000}",
    )
    try:
        await connection.execute("SELECT 1")
    finally:
        await connection.close()


@router.get("/health", responses={503: {"model": HealthResponse}})
async def get_health(request: Request, response: Response) -> HealthResponse:
    version = request.app.version
    if not uses_health_db():
        return HealthResponse(version=version)

    try:
        # Repeated cancellation also interrupts psycopg's query cancellation wait.
        with fail_after(_DB_TIMEOUT_SECONDS):
            await _check_db()
    except (PostgresError, OSError, RuntimeError):
        response.status_code = 503
        return HealthResponse(
            status="degraded", db="unavailable", redis="not_configured",
            version=version, is_mock=False,
        )
    return HealthResponse(db="ok", redis="not_configured", version=version, is_mock=False)
