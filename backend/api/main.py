import re
import secrets
import string
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from api.errors import (
    ApiError,
    error_response,
    handle_api_error,
    handle_http_error,
    handle_unexpected_error,
    handle_validation_error,
)
from api.request_logs import private_endpoint, request_logger
import api.routers.accounts.favorites as favorites, api.routers.festivals.info as info
from api.routers import health
from api.routers.accounts import auth
from api.routers.assistant import chatbot
from api.routers.festivals import catalog
from api.routers.festivals.catalog import uses_festival_db
from api.routers.routes import routes
from api.services.real_routes import uses_real_routes
from api.services.seoul_crowd import uses_real_crowd

app = FastAPI(title="놀다가 API (mock)", version="0.1.0-mock")
app.add_exception_handler(ApiError, handle_api_error)
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
        alphabet = string.ascii_letters + string.digits
        request_id = "req_" + "".join(secrets.choice(alphabet) for _ in range(26))
    request.state.request_id = request_id
    endpoint = private_endpoint(request.url.path)
    try:
        response = await call_next(request)
    except Exception as error:
        if endpoint is None:
            raise
        # The server traceback can contain input values from an unexpected error.
        response = await handle_unexpected_error(request, error)
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
    if not _serves_real_data(request):
        response.headers["X-Mock"] = "true"
    elif "X-Mock" in response.headers and (
        _REAL_ROUTE_PATHS.match(request.url.path) or _REAL_CROWD_PATH.match(request.url.path)
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
_REAL_ROUTE_PATHS = re.compile(r"^/api/v1/routes/(return|visit)(/[^/]+)?/?$")
_REAL_CROWD_PATH = re.compile(r"^/api/v1/festivals/[^/]+/crowd/?$")


def _serves_real_data(request: Request) -> bool:
    path = request.url.path
    return (
        (uses_festival_db() and bool(_REAL_FESTIVAL_PATHS.match(path)))
        or (uses_real_routes() and bool(_REAL_ROUTE_PATHS.match(path)))
        or (uses_real_crowd() and bool(_REAL_CROWD_PATH.match(path)))
    )


for module in (health, catalog, routes, chatbot, auth):
    app.include_router(module.router, prefix="/api/v1")
for module in (info, favorites): app.include_router(module.router, prefix="/api/v1")
