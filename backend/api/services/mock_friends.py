from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from api.mocks.store import auth_lock, users_by_email
from api.schemas.friends import (
    ACTION_STATUS,
    FRIENDS_PAGE_SIZE,
    FriendItem,
    FriendList,
    FriendRequestItem,
    FriendRequestList,
    FriendRequestResult,
    FriendSearchItem,
    FriendSearchResult,
    FriendshipStatus,
    RequestAction,
    RequestBox,
    RequestStatus,
)
from api.services import friends as rules
from api.services.mock_auth import authenticated_access


@dataclass
class _Request:
    request_id: str
    sender: UUID
    recipient: UUID
    created_at: datetime
    status: RequestStatus = "pending"
    responded_at: datetime | None = None

    @property
    def pair(self) -> frozenset[UUID]:
        return frozenset((self.sender, self.recipient))


class MockFriends:
    def __init__(self) -> None:
        self.requests: dict[str, _Request] = {}
        self.friendships: dict[frozenset[UUID], datetime] = {}
        self.blocks: set[tuple[UUID, UUID]] = set()

    def _pending(self, pair: frozenset[UUID]) -> _Request | None:
        return next((row for row in self.requests.values()
                     if row.status == "pending" and row.pair == pair), None)

    def _blocked(self, actor: UUID, other: UUID) -> bool:
        return (actor, other) in self.blocks or (other, actor) in self.blocks

    def _resolve(self, row: _Request, status: RequestStatus) -> FriendRequestResult:
        now = datetime.now(timezone.utc)
        row.status = status
        row.responded_at = now
        if status == "accepted":
            self.friendships[row.pair] = now
        return FriendRequestResult(request_id=row.request_id, status=status)

    def remove_account(self, user_id: UUID) -> None:
        self.requests = {key: row for key, row in self.requests.items() if user_id not in row.pair}
        self.friendships = {pair: since for pair, since in self.friendships.items() if user_id not in pair}
        self.blocks = {pair for pair in self.blocks if user_id not in pair}

    def prune_expired(self, now: datetime) -> None:
        cutoff = now - timedelta(days=30)
        for key, row in list(self.requests.items()):
            if row.status in ("rejected", "cancelled") and row.responded_at is not None and row.responded_at <= cutoff:
                del self.requests[key]

    def search(self, actor: UUID, nickname: str) -> FriendSearchResult:
        rules.enforce_search_limit(actor)
        for user in users_by_email.values():
            if user.display_name.lower() != nickname.lower():
                continue
            other = UUID(user.user_id)
            if actor == other or self._blocked(actor, other):
                break
            pair = frozenset((actor, other))
            pending = self._pending(pair)
            status: FriendshipStatus = "none"
            if pair in self.friendships:
                status = "friends"
            elif pending:
                status = "pending_sent" if pending.sender == actor else "pending_received"
            return FriendSearchResult(items=[FriendSearchItem(
                user_id=other, display_name=user.display_name, friendship_status=status,
            )])
        return FriendSearchResult(items=[])

    def create_request(self, actor: UUID, other: UUID) -> FriendRequestResult:
        if actor == other or _display_name(other) is None:
            raise rules.user_not_found()
        if self._blocked(actor, other):
            raise rules.blocked()
        pair = frozenset((actor, other))
        if pair in self.friendships:
            raise rules.already_friends()
        pending = self._pending(pair)
        if pending:
            if pending.sender == actor:
                raise rules.request_pending()
            return self._resolve(pending, "accepted")

        request_id = rules.new_request_id()
        self.requests[request_id] = _Request(request_id, actor, other, datetime.now(timezone.utc))
        return FriendRequestResult(request_id=request_id, status="pending")

    def act_on_request(self, actor: UUID, request_id: str, action: RequestAction) -> FriendRequestResult:
        row = self.requests.get(request_id)
        if row is None:
            raise rules.request_not_found()
        rules.check_request_action(actor, row.sender, row.recipient, row.status, action)
        if action == "accept" and self._blocked(row.sender, row.recipient):
            raise rules.blocked()
        return self._resolve(row, ACTION_STATUS[action])

    def list_requests(self, actor: UUID, box: RequestBox) -> FriendRequestList:
        rows = sorted(self.requests.values(), key=lambda row: (row.created_at, row.request_id), reverse=True)
        items = []
        for row in rows:
            owner, other = (row.recipient, row.sender) if box == "received" else (row.sender, row.recipient)
            if owner == actor:
                items.append(FriendRequestItem(
                    request_id=row.request_id, user_id=other, display_name=_display_name(other),
                    status=row.status, created_at=row.created_at,
                ))
        return FriendRequestList(items=items)

    def list_friends(self, actor: UUID, page: int) -> FriendList:
        rows = [(next(iter(pair - {actor})), since) for pair, since in self.friendships.items() if actor in pair]
        rows.sort(key=lambda row: row[0])
        rows.sort(key=lambda row: row[1], reverse=True)
        start = (page - 1) * FRIENDS_PAGE_SIZE
        return FriendList(items=[
            FriendItem(user_id=other, display_name=_display_name(other), since=since)
            for other, since in rows[start:start + FRIENDS_PAGE_SIZE]
        ])

    def delete_friend(self, actor: UUID, other: UUID) -> None:
        self.friendships.pop(frozenset((actor, other)), None)

    def block_user(self, actor: UUID, other: UUID) -> None:
        if _display_name(other) is None:
            return
        self.blocks.add((actor, other))
        self.delete_friend(actor, other)
        pending = self._pending(frozenset((actor, other)))
        if pending:
            self._resolve(pending, "cancelled")

    def unblock_user(self, actor: UUID, other: UUID) -> bool:
        if (actor, other) not in self.blocks:
            return False
        self.blocks.remove((actor, other))
        return True


def _display_name(user_id: UUID) -> str | None:
    return next((user.display_name for user in users_by_email.values() if user.user_id == str(user_id)), None)


store = MockFriends()


def run[T](authorization: str | None, operation: Callable[[UUID], T]) -> T:
    with auth_lock:
        now = datetime.now(timezone.utc)
        _, access = authenticated_access(authorization, now)
        store.prune_expired(now)
        return operation(UUID(access.user_id))
