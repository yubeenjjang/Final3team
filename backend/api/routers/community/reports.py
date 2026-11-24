from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from api.deps import AuthenticatedSession
from api.repositories import reports as repository
from api.schemas import reports as schema
from api.services import mock_reports, reports as rules
from api.services.chat import ChatUser

router = APIRouter(prefix="/reports")


@router.post("", status_code=201)
async def submit(request: schema.ReportCreate, user: ChatUser, auth: AuthenticatedSession) -> schema.ReportCreated:
    target = rules.target_id(request)
    if auth is None:
        return await run_in_threadpool(mock_reports.mock_reports.submit, user.user_id, request, target)
    room = await repository.visible_target_room(auth[1], request.target_type, target)
    return await run_in_threadpool(repository.submit, user.user_id, request, target, room)
