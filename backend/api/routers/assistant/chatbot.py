from typing import Annotated

from fastapi import APIRouter, Header, Path, Request

from api.schemas.assistant import RUN_ID_PATTERN, AssistantRequest
from api.services.mock_assistant import create_run, get_run

router = APIRouter()
RunId = Annotated[str, Path(pattern=RUN_ID_PATTERN)]
RunToken = Annotated[str | None, Header(alias="X-Run-Access-Token")]


@router.post("/assistant/runs", status_code=202)
async def submit_run(request: Request, run: AssistantRequest) -> dict[str, object]:
    return create_run(run, await request.json())


@router.get("/assistant/runs/{run_id}")
def fetch_run(run_id: RunId, token: RunToken = None) -> dict[str, object]:
    return get_run(run_id, token)
