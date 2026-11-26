from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

RequestStatus = Literal["pending", "accepted", "rejected", "cancelled"]
RequestAction = Literal["accept", "reject", "cancel"]
RequestBox = Literal["received", "sent"]
FriendshipStatus = Literal["none", "pending_sent", "pending_received", "friends"]

FRIENDS_PAGE_SIZE = 20
FRIEND_REQUEST_ID_PATTERN = r"^frq_[0-9A-Za-z]{6,26}$"
ACTION_STATUS: dict[RequestAction, RequestStatus] = {
    "accept": "accepted", "reject": "rejected", "cancel": "cancelled",
}


class FriendRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to_user_id: UUID


class FriendRequestResult(BaseModel):
    request_id: str
    status: RequestStatus


class FriendSearchItem(BaseModel):
    user_id: UUID
    display_name: str
    friendship_status: FriendshipStatus


class FriendSearchResult(BaseModel):
    items: list[FriendSearchItem]


class FriendRequestItem(FriendRequestResult):
    user_id: UUID
    display_name: str | None
    created_at: datetime


class FriendRequestList(BaseModel):
    items: list[FriendRequestItem]


class FriendItem(BaseModel):
    user_id: UUID
    display_name: str | None
    since: datetime


class FriendList(BaseModel):
    items: list[FriendItem]


class BlockResult(BaseModel):
    blocked: Literal[True] = True
