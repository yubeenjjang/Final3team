from typing import Annotated

from fastapi import APIRouter, Header, Path, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from api.schemas.routes import (
    ROUTE_REQUEST_ID_PATTERN,
    ReturnRouteRequest,
    VisitRouteRequest,
)
from api.services import real_routes
from api.services.mock_routes import create_route, get_route

router = APIRouter()
RouteId = Annotated[str, Path(pattern=ROUTE_REQUEST_ID_PATTERN)]
RouteToken = Annotated[str | None, Header(alias="X-Route-Access-Token")]
ScenarioHeader = Annotated[str, Header(alias="X-Mock-Scenario")]


@router.post("/routes/return", responses={202: {"description": "경로 요청 접수"}})
async def submit_return_route(
    request: Request,
    route: ReturnRouteRequest,
    scenario: ScenarioHeader = "async_ready",
) -> JSONResponse:
    submitted_body = await request.json()
    if real_routes.uses_real_routes():
        status, body = await real_routes.get_service().create_route("return", route, submitted_body)
    else:
        status, body = create_route("return", route, submitted_body, scenario)
    return JSONResponse(body, status_code=status)


@router.get("/routes/return/{route_request_id}")
async def get_return_route(route_request_id: RouteId, token: RouteToken = None) -> dict[str, object]:
    if real_routes.uses_real_routes():
        return real_routes.get_service().get_route("return", route_request_id, token)
    return await run_in_threadpool(get_route, "return", route_request_id, token)


@router.post("/routes/visit", responses={202: {"description": "경로 요청 접수"}})
async def submit_visit_route(
    request: Request,
    route: VisitRouteRequest,
    scenario: ScenarioHeader = "async_ready",
) -> JSONResponse:
    submitted_body = await request.json()
    if real_routes.uses_real_routes():
        status, body = await real_routes.get_service().create_route("visit", route, submitted_body)
    else:
        status, body = create_route("visit", route, submitted_body, scenario)
    return JSONResponse(body, status_code=status)


@router.get("/routes/visit/{route_request_id}")
async def get_visit_route(route_request_id: RouteId, token: RouteToken = None) -> dict[str, object]:
    if real_routes.uses_real_routes():
        return real_routes.get_service().get_route("visit", route_request_id, token)
    return await run_in_threadpool(get_route, "visit", route_request_id, token)
