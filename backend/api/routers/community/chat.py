from typing import Annotated, cast, get_args

from fastapi import APIRouter, Depends, Path, Query, Response
from starlette.concurrency import run_in_threadpool

from api.deps import AuthenticatedSession
from api.errors import ApiError
from api.realtime import chat_socket as realtime
from api.repositories import chat as repository
from api.routers.community import companions
from api.schemas.chat import (
    MAX_BIGINT, ROOM_ID_PATTERN, Action, EmptyBody, Invitations, ReadRoom, RenameRoom, RoomCreate, RoomFilter,
)
from api.services import mock_chat
from api.services.chat import ChatRooms as ChatRooms
from api.services.chat import ChatUser

router = APIRouter()
RoomPath = Annotated[str, Path(pattern=ROOM_ID_PATTERN)]
QuerySeq = Annotated[int, Query(ge=0, le=MAX_BIGINT)]
_ROOM_ACTIONS = get_args(Action)


def room_action(action: Annotated[str, Path(json_schema_extra={"enum": list(_ROOM_ACTIONS)})]) -> Action:
    if action not in _ROOM_ACTIONS:
        raise ApiError(404, "NOT_FOUND", "요청한 주소를 찾을 수 없습니다.")
    return cast(Action, action)


@router.get("/me/chat-rooms")
async def list_rooms(user: ChatUser, auth: AuthenticatedSession, filter: RoomFilter = "all") -> dict:
    if auth:
        rooms = await repository.list_rooms(auth[1], user.user_id, filter)
    else:
        rooms = await run_in_threadpool(companions.memory.list_chat_rooms, user.user_id, filter)
    if not rooms:
        return {"items": [], "empty_hint": "동행을 찾거나 친구를 추가해 보세요"}
    return {"items": rooms}


@router.post("/chat-rooms", status_code=201)
async def create_room(request: RoomCreate, response: Response, user: ChatUser) -> dict:
    store = repository.ChatRooms if user.claims else mock_chat.mock_rooms
    room_id, created = await run_in_threadpool(store.create, user.user_id, request)
    if not created:
        response.status_code = 200
    elif request.type == "friend_group":
        for invitee in request.invitee_ids:
            await realtime.publish(realtime.user_topic(invitee))
    return {"room_id": room_id}


@router.post("/chat-rooms/{room_id}/invitations")
async def invite(room_id: RoomPath, request: Invitations, user: ChatUser) -> dict:
    store = repository.ChatRooms if user.claims else mock_chat.mock_rooms
    invited = await run_in_threadpool(store.invite, user.user_id, room_id, request.invitee_ids)
    for member in invited:
        await realtime.publish(realtime.user_topic(member["user_id"]))
    return {"room_id": room_id, "invited": invited}


@router.post("/chat-rooms/{room_id}/read", status_code=204)
async def mark_read(room_id: RoomPath, request: ReadRoom, user: ChatUser) -> Response:
    store = repository.ChatRooms if user.claims else mock_chat.mock_rooms
    await run_in_threadpool(store.read, user.user_id, room_id, request.seq)
    return Response(status_code=204)


# Place the literal /read and /invitations POST routes before /{action}.
@router.post("/chat-rooms/{room_id}/{action}")
async def act(room_id: RoomPath, action: Annotated[Action, Depends(room_action)], user: ChatUser) -> dict:
    store = repository.ChatRooms if user.claims else mock_chat.mock_rooms
    status, _ = await run_in_threadpool(store.act, user.user_id, room_id, action)
    await realtime.publish(realtime.room_topic(room_id))
    return {"room_id": room_id, "my_status": status}


@router.patch("/chat-rooms/{room_id}")
async def rename(room_id: RoomPath, request: RenameRoom, user: ChatUser) -> dict:
    store = repository.ChatRooms if user.claims else mock_chat.mock_rooms
    await run_in_threadpool(store.rename, user.user_id, room_id, request.name)
    return {"room_id": room_id, "name": request.name}


@router.get("/chat-rooms/{room_id}/messages")
async def history(
    room_id: RoomPath, user: ChatUser, auth: AuthenticatedSession,
    after_seq: QuerySeq | None = None, before_seq: QuerySeq | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    if auth:
        _, denied = await repository.room_access(auth[1], user.user_id, room_id)
        if denied:
            raise repository.forbidden()
        items, more = await repository.messages(auth[1], room_id, after_seq, before_seq, limit)
    else:
        items, more = mock_chat.mock_rooms.messages(user.user_id, room_id, after_seq, before_seq, limit)
    return {"items": items, "has_more": more}


@router.post("/ws-tickets", status_code=201)
async def ticket(request: EmptyBody, user: ChatUser, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return {"ticket": realtime.tickets.issue(user), "expires_in": realtime.TICKET_TTL}
