from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

ROOM_ID_PATTERN = r"^crm_[0-9A-Za-z]{6,26}$"
MAX_BIGINT = 2**63 - 1
PAGE_SIZE = 20
RoomID = Annotated[str, Field(pattern=ROOM_ID_PATTERN)]
Seq = Annotated[int, Field(strict=True, ge=0, le=MAX_BIGINT)]


def valid_text(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("유효한 UTF-8 문자열이 필요합니다.") from None
    if "\x00" in value:
        raise ValueError("문자열에 NUL을 넣을 수 없습니다.")
    return value


Name = Annotated[str, Field(min_length=1, max_length=40), AfterValidator(valid_text)]
Action = Literal["accept", "decline", "leave"]
RoomFilter = Literal["all", "companion", "friend", "past"]


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class DirectRoom(ChatInput):
    type: Literal["direct"]
    friend_id: UUID


class GroupRoom(ChatInput):
    type: Literal["friend_group"]
    name: Name
    invitee_ids: Annotated[list[UUID], Field(min_length=2, max_length=19)]


RoomCreate = Annotated[DirectRoom | GroupRoom, Field(discriminator="type")]


class Invitations(ChatInput):
    invitee_ids: list[UUID]


class RenameRoom(ChatInput):
    name: Name


class ReadRoom(ChatInput):
    seq: Seq


class EmptyBody(ChatInput):
    pass


class ReadNotificationsByID(ChatInput):
    ids: list[Annotated[int, Field(strict=True, ge=1, le=MAX_BIGINT)]]


class ReadAllNotifications(ChatInput):
    all: Literal[True]


class NotificationItem(BaseModel):
    notification_id: int
    type: str
    ref_type: str
    ref_id: str
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationItem]
    unread_count: int


class Subscribe(ChatInput):
    type: Literal["subscribe"]
    room_id: RoomID
    after_seq: Seq


class Send(ChatInput):
    type: Literal["send"]
    room_id: RoomID
    client_message_id: Annotated[str, Field(min_length=8, max_length=64), AfterValidator(valid_text)]
    body: Annotated[str, Field(min_length=1, max_length=1000), AfterValidator(valid_text)]
