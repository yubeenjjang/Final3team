from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import time
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from api.auth import service, state
from api.auth.tokens import AccessClaims, unauthorized, uses_auth_db
from api.deps import Authorization, CurrentUser, get_current_user
from api.errors import ApiError
from api.mocks.store import auth_lock
from api.repositories.chat import ChatRooms as PostgresChatRooms
from api.services import mock_chat
from api.services.mock_auth import authenticated_access


@dataclass(frozen=True)
class ChatIdentity:
    user_id: UUID
    claims: AccessClaims | None = None
    mock_authorization: str | None = field(default=None, repr=False)


def _mock_identity(authorization: str | None) -> ChatIdentity:
    with auth_lock:
        _, access = authenticated_access(authorization, datetime.now(timezone.utc))
        return ChatIdentity(UUID(access.user_id), mock_authorization=authorization)


async def _identity(
    user: Annotated[CurrentUser | None, Depends(get_current_user)],
    authorization: Authorization = None,
) -> ChatIdentity:
    if user is not None:
        return ChatIdentity(user.claims.user_id, claims=user.claims)
    if uses_auth_db():
        raise unauthorized()
    return await run_in_threadpool(_mock_identity, authorization)


ChatUser = Annotated[ChatIdentity, Depends(_identity)]


def is_current(identity: ChatIdentity) -> bool:
    if identity.claims is None:
        try:
            return _mock_identity(identity.mock_authorization).user_id == identity.user_id
        except ApiError:
            return False
    if time() >= identity.claims.expires_at:
        return False
    try:
        return (
            not state.get_auth_state().is_revoked(identity.claims.jti)
            and service.account_is_active(identity.user_id)
        )
    except state.AuthStateUnavailable:
        return False


class ChatRooms:
    """동행·친구 서비스에서 동기 호출하는 진입점. DB 호출은 같은 트랜잭션을 넘길 수 있다."""

    @staticmethod
    def create_companion_room(post_id: str, owner_id: UUID, *, db: Session | None = None) -> str:
        owner_id = UUID(str(owner_id))
        if db is not None or uses_auth_db():
            return PostgresChatRooms.create_companion_room(post_id, owner_id, db=db)
        return mock_chat.mock_rooms.create_companion_room(post_id, owner_id)

    @staticmethod
    def add_member(room_id: str, user_id: UUID, *, db: Session | None = None) -> None:
        user_id = UUID(str(user_id))
        if db is not None or uses_auth_db():
            PostgresChatRooms.add_member(room_id, user_id, db=db)
        else:
            mock_chat.mock_rooms.add_member(room_id, user_id)

    @staticmethod
    def close_direct_room_on_unblock(user_a: UUID, user_b: UUID, *, db: Session | None = None) -> None:
        user_a, user_b = UUID(str(user_a)), UUID(str(user_b))
        if db is not None or uses_auth_db():
            PostgresChatRooms.close_direct_room_on_unblock(user_a, user_b, db=db)
        else:
            mock_chat.mock_rooms.close_direct_room_on_unblock(user_a, user_b)
