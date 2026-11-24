from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response
from starlette.concurrency import run_in_threadpool

from api.deps import Authorization
from api.errors import ApiError
from api.repositories import friends as repository
from api.routers.accounts.dependencies import MeSession
from api.schemas.friends import (
    FRIEND_REQUEST_ID_PATTERN,
    BlockResult,
    FriendList,
    FriendRequestCreate,
    FriendRequestList,
    FriendRequestResult,
    FriendSearchResult,
    RequestAction,
    RequestBox,
)
from api.services import friends as rules, mock_friends

router = APIRouter()


@router.get("/users/search")
async def search_users(
    nickname: Annotated[str, Query(min_length=2, max_length=12)],
    auth: MeSession,
    authorization: Authorization = None,
) -> FriendSearchResult:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: mock_friends.store.search(actor, nickname),
        )
    rules.enforce_search_limit(auth[0].claims.user_id)
    return await repository.search(auth[1], nickname)


@router.post("/friend-requests", status_code=201)
async def create_friend_request(
    request: FriendRequestCreate, auth: MeSession, authorization: Authorization = None,
) -> FriendRequestResult:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: mock_friends.store.create_request(actor, request.to_user_id),
        )
    return await run_in_threadpool(repository.create_request, auth[0].claims.user_id, request.to_user_id)


@router.get("/me/friend-requests")
async def list_friend_requests(
    auth: MeSession, box: RequestBox = "received", authorization: Authorization = None,
) -> FriendRequestList:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: mock_friends.store.list_requests(actor, box),
        )
    return await repository.list_requests(auth[1], box)


@router.post("/friend-requests/{request_id}/{action}")
async def act_on_friend_request(
    request_id: Annotated[str, Path(pattern=FRIEND_REQUEST_ID_PATTERN)],
    action: RequestAction,
    auth: MeSession,
    authorization: Authorization = None,
) -> FriendRequestResult:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization,
            lambda actor: mock_friends.store.act_on_request(actor, request_id, action),
        )
    actor = auth[0].claims.user_id
    other = await repository.request_recipient_or_sender(auth[1], actor, request_id, action)
    return await run_in_threadpool(repository.act_on_request, actor, other, request_id, action)


@router.get("/me/friends")
async def list_friends(
    auth: MeSession, page: Annotated[int, Query(ge=1)] = 1, authorization: Authorization = None,
) -> FriendList:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: mock_friends.store.list_friends(actor, page),
        )
    return await repository.list_friends(auth[1], page)


@router.delete("/me/friends/{user_id}", status_code=204)
async def delete_friend(user_id: UUID, auth: MeSession, authorization: Authorization = None) -> Response:
    if auth is None:
        await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: mock_friends.store.delete_friend(actor, user_id),
        )
    else:
        await run_in_threadpool(repository.delete_friend, auth[0].claims.user_id, user_id)
    return Response(status_code=204)


def _block(actor: UUID, other: UUID, write: Callable[[UUID, UUID], None]) -> BlockResult:
    if actor == other:
        raise ApiError(422, "VALIDATION_ERROR", "자기 자신은 차단할 수 없습니다.")
    write(actor, other)
    return BlockResult()


@router.put("/me/blocks/{user_id}")
async def block_user(user_id: UUID, auth: MeSession, authorization: Authorization = None) -> BlockResult:
    if auth is None:
        return await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: _block(actor, user_id, mock_friends.store.block_user),
        )
    return await run_in_threadpool(_block, auth[0].claims.user_id, user_id, repository.block_user)


@router.delete("/me/blocks/{user_id}", status_code=204)
async def unblock_user(user_id: UUID, auth: MeSession, authorization: Authorization = None) -> Response:
    if auth is None:
        blocker, removed = await run_in_threadpool(
            mock_friends.run, authorization, lambda actor: (actor, mock_friends.store.unblock_user(actor, user_id)),
        )
    else:
        blocker = auth[0].claims.user_id
        removed = await run_in_threadpool(repository.unblock_user, blocker, user_id)
    if removed:
        await run_in_threadpool(rules.notify_chat_unblocked, blocker, user_id)
    return Response(status_code=204)
