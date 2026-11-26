from typing import Annotated

from fastapi import APIRouter, Header, Path, Query, Request, Response
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from api.deps import Authorization
from api.schemas.routes import (
    ROUTE_REQUEST_ID_PATTERN,
    ReturnRouteRequest,
    VisitRouteRequest,
)
from api.services import bus_crowding, mock_routes, real_routes, route_rate_limit
from api.services.mock_routes import create_route, get_route

router = APIRouter()
RouteId = Annotated[str, Path(pattern=ROUTE_REQUEST_ID_PATTERN)]
RouteToken = Annotated[str | None, Header(alias="X-Route-Access-Token")]
ScenarioHeader = Annotated[str, Header(alias="X-Mock-Scenario")]


@router.post("/routes/return", responses={
    200: {"headers": {"X-Route-Access-Token": {
        "description": "동기 완료된 경로의 후보를 선택할 때 A05에 보낼 토큰",
        "schema": {"type": "string"},
    }}},
    202: {"description": "경로 요청 접수"},
})
async def submit_return_route(
    request: Request,
    route: ReturnRouteRequest,
    scenario: ScenarioHeader = "async_ready",
    authorization: Authorization = None,
) -> JSONResponse:
    await run_in_threadpool(route_rate_limit.enforce, request.client.host if request.client else "unknown", authorization)
    submitted_body = await request.json()
    if real_routes.uses_real_routes():
        service = real_routes.get_service()
        status, body = await service.create_route("return", route, submitted_body)
        selection_token = service.return_selection_token
    else:
        status, body = await create_route("return", route, submitted_body, scenario)
        selection_token = mock_routes.return_selection_token
    request.state.result_status = body["route_status"]
    request.state.route_request_id = body["route_request_id"]
    headers = {}
    if body["route_status"] == "ready" and body["provider"] != "kakao":
        headers["X-Route-Access-Token"] = await run_in_threadpool(selection_token, body["route_request_id"])
        headers["Cache-Control"] = "private, no-store"
    return JSONResponse(body, status_code=status, headers=headers)


@router.get("/routes/return/{route_request_id}")
async def get_return_route(
    request: Request, response: Response, route_request_id: RouteId, token: RouteToken = None,
    candidate_id: Annotated[str | None, Query(pattern=r"^c[1-9][0-9]*$", max_length=16)] = None,
) -> dict[str, object]:
    live_candidates = None
    if real_routes.uses_real_routes():
        service = real_routes.get_service()
        body = await service.get_route_response("return", route_request_id, token)
        if candidate_id is not None and body["route_status"] == "ready":
            live_candidates = service.live_candidates_for_selection(route_request_id)
    else:
        body = await run_in_threadpool(get_route, "return", route_request_id, token)
    if candidate_id is not None:
        body = await bus_crowding.selected_candidate(body, candidate_id, live_candidates)
        response.headers["Cache-Control"] = "private, no-store"
    request.state.result_status = body["route_status"]
    request.state.route_request_id = body["route_request_id"]
    return body


@router.post("/routes/visit", responses={202: {"description": "경로 요청 접수"}})
async def submit_visit_route(
    request: Request,
    route: VisitRouteRequest,
    scenario: ScenarioHeader = "async_ready",
    authorization: Authorization = None,
) -> JSONResponse:
    await run_in_threadpool(route_rate_limit.enforce, request.client.host if request.client else "unknown", authorization)
    submitted_body = await request.json()
    if real_routes.uses_real_routes():
        status, body = await real_routes.get_service().create_route("visit", route, submitted_body)
    else:
        status, body = await create_route("visit", route, submitted_body, scenario)
    request.state.result_status = body["route_status"]
    request.state.route_request_id = body["route_request_id"]
    return JSONResponse(body, status_code=status)


@router.get("/routes/visit/{route_request_id}")
async def get_visit_route(
    request: Request, route_request_id: RouteId, token: RouteToken = None,
) -> dict[str, object]:
    if real_routes.uses_real_routes():
        body = await real_routes.get_service().get_route_response("visit", route_request_id, token)
    else:
        body = await run_in_threadpool(get_route, "visit", route_request_id, token)
    request.state.result_status = body["route_status"]
    request.state.route_request_id = body["route_request_id"]
    return body
