"""In-process chat fixtures for AUTH_PROVIDER=mock."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import count
from threading import Lock
from uuid import UUID

from ulid import ULID

from api.mocks.store import auth_lock, users_by_email
from api.repositories.chat import (
    blocked, companion_room_id, forbidden, invalid_state, invitees, not_friends, read_only,
)
from api.schemas.chat import Action, DirectRoom, GroupRoom, PAGE_SIZE, RoomFilter


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Member:
    status: str
    last_read_seq: int = 0
    joined_at: datetime | None = None


@dataclass
class Room:
    room_type: str
    owner: UUID | None = None
    name: str | None = None
    festival_name: str | None = None
    meet_at: datetime | None = None
    status: str = "active"
    closed_by_block: bool = False
    read_only_at: datetime | None = None
    members: dict[UUID, Member] = field(default_factory=dict)
    messages: list[dict] = field(default_factory=list)
    sent: dict[tuple[UUID, str], tuple[int, int]] = field(default_factory=dict)


class MockChatRooms:
    def __init__(self) -> None:
        self.lock = Lock()
        self.rooms: dict[str, Room] = {}
        self.friendships: set[frozenset[UUID]] = set()
        self.blocks: set[tuple[UUID, UUID]] = set()
        self.alerts: dict[UUID, list[dict]] = {}
        self.ids = count(1)
        self.alert_ids = count(1)

    def _blocked(self, a: UUID, b: UUID) -> bool:
        return (a, b) in self.blocks or (b, a) in self.blocks

    def _friends(self, actor: UUID, users: list[UUID], *, direct: bool = False) -> None:
        for user in users:
            if self._blocked(actor, user) and direct:
                raise blocked()
            if self._blocked(actor, user) or frozenset((actor, user)) not in self.friendships:
                raise not_friends()

    def _room(self, room_id: str) -> Room:
        if room_id not in self.rooms:
            raise forbidden()
        return self.rooms[room_id]

    def _owner_room(self, actor: UUID, room_id: str) -> Room:
        room = self._room(room_id)
        if room.room_type != "friend_group" or room.owner != actor:
            raise forbidden()
        return room

    def _invite(self, room_id: str, users: list[UUID]) -> list[dict]:
        room = self.rooms[room_id]
        invited = []
        for user in users:
            timestamp = now()
            room.members[user] = Member("invited")
            invited.append({"user_id": user, "status": "invited", "invited_at": timestamp})
            self._add_notification(user, "room_invited", "chat_room", room_id, timestamp)
        return invited

    def create(self, user_id: UUID, request: DirectRoom | GroupRoom) -> tuple[str, bool]:
        with self.lock:
            if isinstance(request, DirectRoom):
                friend = invitees([request.friend_id], user_id)[0]
                self._friends(user_id, [friend], direct=True)
                for room_id, room in self.rooms.items():
                    if room.room_type == "direct" and room.status != "closed" and room.members.keys() == {friend, user_id}:
                        return room_id, False
                room_id = f"crm_{ULID()}"
                self.rooms[room_id] = Room("direct", members={
                    member: Member("joined", joined_at=now()) for member in (user_id, friend)
                })
            else:
                users = invitees(request.invitee_ids, user_id, minimum=2)
                self._friends(user_id, users)
                room_id = f"crm_{ULID()}"
                self.rooms[room_id] = Room(
                    "friend_group", user_id, request.name, members={user_id: Member("joined", joined_at=now())},
                )
                self._invite(room_id, users)
            return room_id, True

    def invite(self, user_id: UUID, room_id: str, target_ids: list[UUID]) -> list[dict]:
        with self.lock:
            room = self._owner_room(user_id, room_id)
            if room.status != "active":
                raise invalid_state()
            users = invitees(target_ids, user_id, minimum=0)
            pending = [target for target in users if target not in room.members
                       or room.members[target].status not in ("invited", "joined")]
            self._friends(user_id, pending)
            return self._invite(room_id, pending)

    def act(self, user_id: UUID, room_id: str, action: Action) -> tuple[str, str]:
        with self.lock:
            room = self._room(room_id)
            member = room.members.get(user_id)
            if member is None or room.room_type == "companion":
                raise forbidden()
            if action == "accept" and member.status == "invited" and room.status == "active":
                room.members[user_id] = Member("joined", len(room.messages), now())
                return "joined", room.status
            if action == "decline" and member.status == "invited":
                member.status = "declined"
                return member.status, room.status
            if action != "leave" or member.status != "joined":
                raise invalid_state()
            member.status = "left"
            if room.room_type == "direct":
                room.status = "closed"
            elif room.owner == user_id:
                successors = ((m.joined_at, uid) for uid, m in room.members.items() if m.status == "joined")
                first = min(successors, default=None)
                room.owner = first[1] if first else None
                if room.owner is None:
                    room.status = "closed"
            return member.status, room.status

    def rename(self, user_id: UUID, room_id: str, name: str) -> None:
        with self.lock:
            room = self._owner_room(user_id, room_id)
            if room.status != "active":
                raise forbidden()
            room.name = name

    def create_companion_room(
        self,
        post_id: str,
        owner_id: UUID,
        festival_name: str | None = None,
        meet_at: datetime | None = None,
    ) -> str:
        room_id = companion_room_id(post_id)
        with self.lock:
            room = self.rooms.setdefault(room_id, Room("companion", owner_id))
            if room.room_type != "companion" or room.owner != owner_id:
                raise invalid_state()
            if room.status == "active":
                room.members.setdefault(owner_id, Member("joined", joined_at=now()))
            if festival_name:
                room.festival_name = festival_name
            if meet_at:
                room.meet_at = meet_at
        return room_id

    def add_member(self, room_id: str, user_id: UUID) -> None:
        with self.lock:
            room = self._room(room_id)
            if room.room_type != "companion" or room.status != "active":
                raise invalid_state()
            if user_id not in room.members or room.members[user_id].status != "joined":
                room.members[user_id] = Member("joined", len(room.messages), now())

    def finish_companion_room(self, room_id: str, ended_at: datetime) -> None:
        with self.lock:
            room = self._room(room_id)
            if room.status == "active":
                room.status = "read_only"
            room.read_only_at = ended_at

    def close_direct_room_on_unblock(self, user_a: UUID, user_b: UUID) -> None:
        with self.lock:
            for room in self.rooms.values():
                if room.room_type == "direct" and room.status != "closed" and room.members.keys() == {user_a, user_b}:
                    room.status = "closed"
                    room.closed_by_block = True

    def _access(self, room_id: str, user_id: UUID) -> tuple[str, str | None]:
        room = self.rooms.get(room_id)
        if room is None or user_id not in room.members:
            return "closed", "removed"
        member = room.members[user_id]
        if member.status != "joined":
            return room.status, member.status if member.status in ("left", "removed") else "removed"
        if room.room_type == "direct" and (
            room.closed_by_block or any(self._blocked(user_id, peer) for peer in room.members if peer != user_id)
        ):
            return room.status, "blocked"
        return room.status, None

    def room_access(self, user_id: UUID, room_id: str) -> tuple[str, str | None]:
        with self.lock:
            return self._access(room_id, user_id)

    def read(self, user_id: UUID, room_id: str, seq: int) -> None:
        with self.lock:
            if self._access(room_id, user_id)[1]:
                raise forbidden()
            room = self.rooms[room_id]
            member = room.members[user_id]
            member.last_read_seq = max(member.last_read_seq, min(seq, len(room.messages)))

    def send(self, user_id: UUID, room_id: str, client_id: str, body: str, charge) -> tuple[int, int, bool]:
        with self.lock:
            status, reason = self._access(room_id, user_id)
            if reason:
                raise forbidden()
            room = self.rooms[room_id]
            key = (user_id, client_id)
            if key in room.sent:
                message_id, seq = room.sent[key]
                return message_id, seq, False
            if status != "active":
                raise read_only()
            charge(user_id, room_id)
            message_id, seq = next(self.ids), len(room.messages) + 1
            room.sent[key] = message_id, seq
            room.messages.append({
                "message_id": message_id, "seq": seq, "sender_id": user_id, "msg_type": "text",
                "body": body, "created_at": now(),
            })
            return message_id, seq, True

    def _visible(self, room_id: str, user_id: UUID) -> list[dict]:
        if self._access(room_id, user_id)[1]:
            return []
        room = self.rooms[room_id]
        joined = room.members[user_id].joined_at
        threshold = now() - timedelta(days=30)
        if room.room_type == "companion":
            if room.read_only_at is not None and room.read_only_at <= now() - timedelta(days=3):
                return []
            threshold = joined
        return [m for m in room.messages if m["created_at"] >= joined and m["created_at"] >= threshold
                and m.get("deleted_at") is None]

    def messages(self, user_id: UUID, room_id: str, after: int | None, before: int | None, limit: int):
        with self.lock:
            if self._access(room_id, user_id)[1]:
                raise forbidden()
            candidates = [
                m for m in self._visible(room_id, user_id)
                if (after is None or m["seq"] > after) and (before is None or m["seq"] < before)
            ]
            page = candidates[:limit] if after is not None else candidates[-limit:]
        with auth_lock:
            names = {UUID(user.user_id): user.display_name for user in users_by_email.values()}
        return [dict(m, sender_display_name=names.get(m["sender_id"])) for m in page], len(candidates) > limit

    def list_rooms(self, user_id: UUID, selected: RoomFilter) -> list[dict]:
        with auth_lock:
            names = {UUID(user.user_id): user.display_name for user in users_by_email.values()}
        with self.lock:
            items = []
            for room_id, room in reversed(self.rooms.items()):
                member = room.members.get(user_id)
                if member is None or member.status not in ("invited", "joined"):
                    continue
                if selected == "past" and room.status == "active":
                    continue
                if selected in ("companion", "friend") and (selected == "companion") != (room.room_type == "companion"):
                    continue
                visible = self._visible(room_id, user_id)
                peer_id = next((member_id for member_id in room.members if member_id != user_id), None)
                items.append({
                    "room_id": room_id, "room_type": room.room_type, "name": room.name, "status": room.status,
                    "peer_display_name": names.get(peer_id) if room.room_type == "direct" else None,
                    "festival_name": room.festival_name if room.room_type == "companion" else None,
                    "meet_at": room.meet_at if room.room_type == "companion" else None,
                    "last_message_at": visible[-1]["created_at"] if visible else None,
                    "unread_count": sum(m["seq"] > member.last_read_seq and m["sender_id"] != user_id for m in visible), "my_status": member.status,
                })
            return sorted(items, key=lambda item: item["last_message_at"] or datetime.min.replace(tzinfo=timezone.utc),
                          reverse=True)

    def _notifications(self, user_id: UUID) -> list[dict]:
        cutoff = now() - timedelta(days=90)
        items = [item for item in self.alerts.get(user_id, []) if item["created_at"] > cutoff]
        if items:
            self.alerts[user_id] = items
        else:
            self.alerts.pop(user_id, None)
        return items

    def _add_notification(self, user_id: UUID, event: str, ref_type: str, ref_id: str, timestamp: datetime) -> None:
        items = self._notifications(user_id)
        self.alerts[user_id] = items
        items.append({
            "notification_id": next(self.alert_ids), "created_at": timestamp, "read_at": None,
            "type": event, "ref_type": ref_type, "ref_id": ref_id,
        })

    def notify(self, user_id: UUID, event: str, ref_type: str, ref_id: str) -> None:
        with self.lock:
            self._add_notification(user_id, event, ref_type, ref_id, now())

    def remove_notifications(self, user_id: UUID) -> None:
        with self.lock:
            self.alerts.pop(user_id, None)

    def notifications(self, user_id: UUID, unread_only: bool, page: int) -> dict:
        with self.lock:
            items = self._notifications(user_id)
            unread = sum(item["read_at"] is None for item in items)
            filtered = [dict(item) for item in reversed(items) if not unread_only or item["read_at"] is None]
            return {"items": filtered[(page - 1) * PAGE_SIZE:page * PAGE_SIZE], "unread_count": unread}

    def read_notifications(self, user_id: UUID, ids: list[int] | None) -> None:
        with self.lock:
            timestamp = now()
            for item in self._notifications(user_id):
                if item["read_at"] is None and (ids is None or item["notification_id"] in ids):
                    item["read_at"] = timestamp

    def recent_notifications(self, user_id: UUID, after: int) -> list[dict]:
        with self.lock:
            return [{key: value for key, value in row.items() if key != "read_at"}
                    for row in self._notifications(user_id) if row["notification_id"] > after][:100]

    def notification_head(self, user_id: UUID) -> int:
        with self.lock:
            return max((row["notification_id"] for row in self._notifications(user_id)), default=0)


mock_rooms = MockChatRooms()
