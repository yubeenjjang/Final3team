from fastapi import APIRouter

from api.deps import AuthenticatedSession
from api.repositories import assistant as store
from api.routers.assistant.chatbot import Access, RunId
from api.services import assistant, mock_assistant

router = APIRouter()


@router.get("/assistant/runs/{run_id}")
async def fetch_run(run_id: RunId, access: Access, auth: AuthenticatedSession) -> dict[str, object]:
    if assistant.uses_assistant_db():
        return await store.read(run_id, access, auth[1] if auth else None)
    return await mock_assistant.get_run(run_id, access)
