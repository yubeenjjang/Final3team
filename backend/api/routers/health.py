from fastapi import APIRouter, Request

from api.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health")
async def get_health(request: Request) -> HealthResponse:
    return HealthResponse(version=request.app.version)
