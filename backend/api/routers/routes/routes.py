from typing import Annotated

from fastapi import APIRouter, Header, Path, Request
from fastapi.responses import JSONResponse

from api.schemas.routes import (
    ROUTE_REQUEST_ID_PATTERN,
    ReturnRouteRequest,
    VisitRouteRequest,
)
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
    status, body = create_route("return", route, await request.json(), scenario)
    return JSONResponse(body, status_code=status)


@router.get("/routes/return/{route_request_id}")
def get_return_route(route_request_id: RouteId, token: RouteToken = None) -> dict[str, object]:
    return get_route("return", route_request_id, token)


@router.post("/routes/visit", responses={202: {"description": "경로 요청 접수"}})
async def submit_visit_route(
    request: Request,
    route: VisitRouteRequest,
    scenario: ScenarioHeader = "async_ready",
) -> JSONResponse:
    status, body = create_route("visit", route, await request.json(), scenario)
    return JSONResponse(body, status_code=status)


@router.get("/routes/visit/{route_request_id}")
def get_visit_route(route_request_id: RouteId, token: RouteToken = None) -> dict[str, object]:
    return get_route("visit", route_request_id, token)
