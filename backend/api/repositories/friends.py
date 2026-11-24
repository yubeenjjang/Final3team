from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from api.auth.tokens import unauthorized
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
    RequestAction,
    RequestBox,
    RequestStatus,
)
from api.services import friends as rules
from shared.db.session import service_db_session

# The same cutoff governs request visibility and the retention job.
_EXPIRED = "status IN ('rejected', 'cancelled') AND responded_at <= statement_timestamp() - interval '720 hours'"


async def search(db: AsyncSession, nickname: str) -> FriendSearchResult:
    rows = (await db.execute(text("""
        SELECT u.user_id, u.display_name, CASE
            WHEN f.user_a IS NOT NULL THEN 'friends'
            WHEN r.from_user = me.id THEN 'pending_sent'
            WHEN r.to_user = me.id THEN 'pending_received'
            ELSE 'none'
        END AS friendship_status
        FROM public.app_find_user_by_nickname(:nickname) u
        CROSS JOIN (SELECT public.app_current_user() AS id) me
        LEFT JOIN public.friendships f ON f.user_a = least(me.id, u.user_id)
                                       AND f.user_b = greatest(me.id, u.user_id)
        LEFT JOIN public.friend_requests r ON r.status = 'pending'
             AND least(r.from_user, r.to_user) = least(me.id, u.user_id)
             AND greatest(r.from_user, r.to_user) = greatest(me.id, u.user_id)
    """), {"nickname": nickname})).mappings().all()
    return FriendSearchResult(items=[FriendSearchItem.model_validate(row) for row in rows])


async def list_requests(db: AsyncSession, box: RequestBox) -> FriendRequestList:
    owner, other = ("to_user", "from_user") if box == "received" else ("from_user", "to_user")
    rows = (await db.execute(text(f"""
        SELECT request_id, {other} AS user_id, public.app_public_display_name({other}) AS display_name,
               status, created_at
        FROM public.friend_requests
        WHERE {owner} = public.app_current_user() AND NOT ({_EXPIRED})
        ORDER BY created_at DESC, request_id DESC
    """))).mappings().all()
    return FriendRequestList(items=[FriendRequestItem.model_validate(row) for row in rows])


async def list_friends(db: AsyncSession, page: int) -> FriendList:
    offset = (page - 1) * FRIENDS_PAGE_SIZE
    if offset > 2**63 - 1:
        return FriendList(items=[])
    rows = (await db.execute(text("""
        SELECT user_id, public.app_public_display_name(user_id) AS display_name, since
        FROM (
            SELECT CASE WHEN user_a = me.id THEN user_b ELSE user_a END AS user_id, created_at AS since
            FROM public.friendships
            CROSS JOIN (SELECT public.app_current_user() AS id) me
            WHERE me.id IN (user_a, user_b)
            ORDER BY since DESC, user_id
            LIMIT :limit OFFSET :offset
        ) page
        ORDER BY since DESC, user_id
    """), {"limit": FRIENDS_PAGE_SIZE, "offset": offset})).mappings().all()
    return FriendList(items=[FriendItem.model_validate(row) for row in rows])


async def request_recipient_or_sender(
    db: AsyncSession, actor: UUID, request_id: str, action: RequestAction,
) -> UUID:
    row = (await db.execute(text(f"""
        SELECT from_user, to_user, status
        FROM public.friend_requests WHERE request_id = :id AND NOT ({_EXPIRED})
    """), {"id": request_id})).one_or_none()
    if row is None:
        raise rules.request_not_found()
    rules.check_request_action(actor, row.from_user, row.to_user, row.status, action)
    return row.to_user if actor == row.from_user else row.from_user


def lock_users(db: Session, actor: UUID, other: UUID) -> str | None:
    # Every friend mutation takes user locks in UUID order. A80 locks its user
    # row before deleting relationships, so concurrent writes see the new status.
    states = dict(db.execute(text("""
        SELECT user_id, status FROM public.users
        WHERE user_id IN (:actor, :other)
        ORDER BY user_id FOR NO KEY UPDATE
    """), {"actor": actor, "other": other}).tuples().all())
    if states.get(actor) != "active":
        raise unauthorized()
    return states.get(other)


def _blocked(db: Session, actor: UUID, other: UUID) -> bool:
    return db.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM public.user_blocks
            WHERE (blocker = :actor AND blocked = :other) OR (blocker = :other AND blocked = :actor)
        )
    """), {"actor": actor, "other": other})


def _resolve(
    db: Session, request_id: str, status: RequestStatus, pair: dict[str, UUID],
) -> FriendRequestResult:
    db.execute(text("""
        UPDATE public.friend_requests SET status = :status, responded_at = statement_timestamp()
        WHERE request_id = :id
    """), {"id": request_id, "status": status})
    if status == "accepted":
        db.execute(text("""
            INSERT INTO public.friendships (user_a, user_b, request_id, created_at)
            VALUES (:a, :b, :id, statement_timestamp())
        """), {**pair, "id": request_id})
    return FriendRequestResult(request_id=request_id, status=status)


def _pair(actor: UUID, other: UUID) -> dict[str, UUID]:
    a, b = sorted((actor, other))
    return {"a": a, "b": b}


def create_request(actor: UUID, other: UUID) -> FriendRequestResult:
    if actor == other:
        raise rules.user_not_found()
    with service_db_session() as db:
        if lock_users(db, actor, other) != "active":
            raise rules.user_not_found()
        if _blocked(db, actor, other):
            raise rules.blocked()
        pair = _pair(actor, other)
        if db.scalar(text("SELECT 1 FROM public.friendships WHERE user_a = :a AND user_b = :b"), pair):
            raise rules.already_friends()
        pending = db.execute(text("""
            SELECT request_id, from_user FROM public.friend_requests
            WHERE status = 'pending' AND least(from_user, to_user) = :a AND greatest(from_user, to_user) = :b
        """), pair).one_or_none()
        if pending is not None:
            if pending.from_user == actor:
                raise rules.request_pending()
            return _resolve(db, pending.request_id, "accepted", pair)

        request_id = rules.new_request_id()
        db.execute(text("""
            INSERT INTO public.friend_requests (request_id, from_user, to_user, created_at)
            VALUES (:id, :actor, :other, statement_timestamp())
        """), {"id": request_id, "actor": actor, "other": other})
        return FriendRequestResult(request_id=request_id, status="pending")


def act_on_request(actor: UUID, other: UUID, request_id: str, action: RequestAction) -> FriendRequestResult:
    with service_db_session() as db:
        other_status = lock_users(db, actor, other)
        pair = _pair(actor, other)
        row = db.execute(text(f"""
            SELECT from_user, to_user, status FROM public.friend_requests
            WHERE request_id = :id AND NOT ({_EXPIRED})
              AND least(from_user, to_user) = :a AND greatest(from_user, to_user) = :b
            FOR UPDATE
        """), {"id": request_id, **pair}).one_or_none()
        if row is None:
            raise rules.request_not_found()
        rules.check_request_action(actor, row.from_user, row.to_user, row.status, action)
        if action == "accept":
            if other_status != "active":
                raise rules.request_not_found()
            if _blocked(db, actor, other):
                raise rules.blocked()
        return _resolve(db, request_id, ACTION_STATUS[action], pair)


def _delete_friend(db: Session, pair: dict[str, UUID]) -> None:
    db.execute(text("DELETE FROM public.friendships WHERE user_a = :a AND user_b = :b"), pair)


def delete_friend(actor: UUID, other: UUID) -> None:
    with service_db_session() as db:
        lock_users(db, actor, other)
        _delete_friend(db, _pair(actor, other))


def block_user(actor: UUID, other: UUID) -> None:
    with service_db_session() as db:
        if lock_users(db, actor, other) in (None, "deleted"):
            return
        db.execute(text("""
            INSERT INTO public.user_blocks (blocker, blocked) VALUES (:actor, :other)
            ON CONFLICT (blocker, blocked) DO NOTHING
        """), {"actor": actor, "other": other})
        pair = _pair(actor, other)
        _delete_friend(db, pair)
        db.execute(text("""
            UPDATE public.friend_requests SET status = 'cancelled', responded_at = statement_timestamp()
            WHERE status = 'pending' AND least(from_user, to_user) = :a AND greatest(from_user, to_user) = :b
        """), pair)
        db.execute(text("""
            UPDATE public.chat_rooms SET status = 'closed'
            WHERE direct_key = :key AND room_type = 'direct' AND status <> 'closed'
        """), {"key": f"{pair['a']}|{pair['b']}"})


def unblock_user(actor: UUID, other: UUID) -> bool:
    with service_db_session() as db:
        lock_users(db, actor, other)
        return db.execute(text("""
            DELETE FROM public.user_blocks WHERE blocker = :actor AND blocked = :other
        """), {"actor": actor, "other": other}).rowcount == 1


def purge_expired_requests() -> int:
    with service_db_session() as db:
        return db.execute(text(f"DELETE FROM public.friend_requests WHERE {_EXPIRED}")).rowcount
