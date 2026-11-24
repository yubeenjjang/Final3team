from typing import Annotated

from fastapi import APIRouter, Query, Response

from api.deps import AuthenticatedSession
from api.repositories import chat as repository
from api.schemas.chat import MAX_BIGINT, PAGE_SIZE, ReadAllNotifications, ReadNotificationsByID
from api.services import mock_chat
from api.services.chat import ChatUser

router = APIRouter(prefix="/me/notifications")


@router.get("")
async def list_notifications(
    user: ChatUser, auth: AuthenticatedSession, unread_only: bool = False,
    page: Annotated[int, Query(ge=1, le=MAX_BIGINT // PAGE_SIZE)] = 1,
) -> dict:
    if auth:
        return await repository.notifications(auth[1], unread_only, page)
    return mock_chat.mock_rooms.notifications(user.user_id, unread_only, page)


@router.post("/read", status_code=204)
async def mark_read(
    request: ReadAllNotifications | ReadNotificationsByID, user: ChatUser, auth: AuthenticatedSession,
) -> Response:
    ids = request.ids if isinstance(request, ReadNotificationsByID) else None
    if auth:
        await repository.read_notifications(auth[1], ids)
    else:
        mock_chat.mock_rooms.read_notifications(user.user_id, ids)
    return Response(status_code=204)
