import re
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import TimeoutError as DBPoolTimeout
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from api.errors import (
    ApiError,
    error_response,
    handle_api_error,
    handle_db_pool_timeout,
    handle_http_error,
    handle_unexpected_error,
    handle_validation_error,
)
from api.auth.state import enforce_login_limit
from api.auth.tokens import uses_auth_db
from api.request_logs import auth_endpoint, chat_endpoint, me_endpoint, private_endpoint, request_logger
from api.realtime import chat_socket
from api.routers import health
from api.routers.accounts import auth, favorites, users
from api.routers.assistant import chatbot
from api.routers.community import chat, notifications
from api.routers.festivals import catalog, info
from api.routers.festivals.catalog import uses_festival_db
from api.routers.routes import routes
from api.services.real_festival_info import uses_real_info
from api.services.real_routes import uses_real_routes
from api.services.seoul_crowd import uses_real_crowd
from ulid import ULID

app = FastAPI(title="놀다가 API (mock)", version="0.1.0-mock")
app.add_exception_handler(ApiError, handle_api_error)
app.add_exception_handler(DBPoolTimeout, handle_db_pool_timeout)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(HTTPException, handle_http_error)
app.add_exception_handler(Exception, handle_unexpected_error)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=[
        "X-Request-ID",
        "X-Route-Access-Token",
        "X-Run-Access-Token",
        "X-Mock-Scenario",
        "Authorization",
    ],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def add_response_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = request.headers.get("X-Request-ID", "")
    if not 1 <= len(request_id) <= 64:
        request_id = "req_" + str(ULID())
    request.state.request_id = request_id
    endpoint = private_endpoint(request.url.path)
    try:
        if endpoint == "/api/v1/auth/login" and request.method == "POST" and uses_auth_db():
            await run_in_threadpool(enforce_login_limit, request.client.host if request.client else "unknown")
        response = await call_next(request)
    except ApiError as error:
        response = await handle_api_error(request, error)
    except Exception as error:
        if endpoint is None:
            raise
        # The server traceback can contain input values from an unexpected error.
        response = await handle_unexpected_error(request, error)
        if uses_auth_db() and (auth_endpoint(request.url.path) or me_endpoint(request.url.path)
                               or chat_endpoint(request.url.path)):
            del response.headers["X-Mock"]
        request_logger.error(
            "endpoint=%s request_id=%r http_status=500 error=INTERNAL_SERVER_ERROR",
            endpoint, request_id,
        )
        return response
    if (
        response.status_code == 400
        and request.method == "OPTIONS"
        and "origin" in request.headers
        and "access-control-request-method" in request.headers
    ):
        response = error_response(
            request,
            ApiError(400, "HTTP_ERROR", "허용되지 않은 교차 출처 요청입니다."),
            {
                name: value
                for name, value in response.headers.items()
                if name.startswith("access-control-") or name == "vary"
            },
        )
    response.headers["X-Request-ID"] = request_id
    if "Retry-After" in response.headers and "access-control-expose-headers" in response.headers:
        response.headers["Access-Control-Expose-Headers"] += ", Retry-After"
    if not _serves_real_data(request):
        response.headers["X-Mock"] = "true"
    elif "X-Mock" in response.headers and (
        _REAL_ROUTE_PATHS.match(request.url.path) or _REAL_CROWD_PATH.match(request.url.path)
        or auth_endpoint(request.url.path) or me_endpoint(request.url.path) or chat_endpoint(request.url.path)
        or _FESTIVAL_INFO_PATH.match(request.url.path)
    ):
        del response.headers["X-Mock"]
    if endpoint is not None:
        request_logger.info(
            "endpoint=%s request_id=%r http_status=%d result_status=%s route_request_id=%s",
            endpoint, request_id, response.status_code, getattr(request.state, "result_status", "-"),
            getattr(request.state, "route_request_id", "-"),
        )
    return response


_REAL_FESTIVAL_PATHS = re.compile(r"^/api/v1/festivals(/fst_[0-9A-Za-z]{6,26})?/?$")
_HEALTH_PATH = re.compile(r"^/api/v1/health/?$")
_REAL_ROUTE_PATHS = re.compile(r"^/api/v1/routes/(return|visit)(/[^/]+)?/?$")
_REAL_CROWD_PATH = re.compile(r"^/api/v1/festivals/[^/]+/crowd/?$")
_FESTIVAL_INFO_PATH = re.compile(r"^/api/v1/festivals/[^/]+/(notices|weather|transit|visit-forecast)/?$")


def _serves_real_data(request: Request) -> bool:
    path = request.url.path
    info_path = _FESTIVAL_INFO_PATH.match(path)
    return (
        (bool(_HEALTH_PATH.match(path)) and health.uses_health_db())
        or (uses_festival_db() and bool(_REAL_FESTIVAL_PATHS.match(path)))
        or (uses_real_routes() and bool(_REAL_ROUTE_PATHS.match(path)))
        or (uses_real_crowd() and bool(_REAL_CROWD_PATH.match(path)))
        or (uses_auth_db() and (auth_endpoint(path) is not None or me_endpoint(path) is not None
                                or chat_endpoint(path) is not None))
        or (info_path is not None and uses_real_info(info_path[1]))
    )


for module in (health, catalog, routes, chatbot, auth):
    app.include_router(module.router, prefix="/api/v1")
for module in (info, favorites, users, chat, notifications, chat_socket):
    app.include_router(module.router, prefix="/api/v1")
