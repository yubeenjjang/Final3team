"""Chat reads use the app role. Multi-row writes use a server transaction."""

import re
from contextlib import nullcontext
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from ulid import ULID

from api.auth.tokens import unauthorized
from api.errors import ApiError
from api.schemas.chat import Action, DirectRoom, GroupRoom, PAGE_SIZE, ROOM_ID_PATTERN, RoomFilter
from shared.db.session import service_db_session


def forbidden() -> ApiError:
    return ApiError(403, "FORBIDDEN", "이 채팅방에 접근할 수 없습니다.")


def invalid_state() -> ApiError:
    return ApiError(409, "ROOM_STATE_CONFLICT", "현재 채팅방 상태에서 처리할 수 없습니다.")


def read_only() -> ApiError:
    return ApiError(403, "ROOM_READ_ONLY", "메시지를 보낼 수 없는 채팅방입니다.")


def not_friends() -> ApiError:
    return ApiError(403, "NOT_FRIENDS", "친구만 채팅에 초대할 수 있습니다.")


def blocked() -> ApiError:
    return ApiError(403, "BLOCKED", "이 사용자와 1:1 채팅을 시작할 수 없습니다.")


def invitees(user_ids: list[UUID], owner_id: UUID, minimum: int = 1) -> list[UUID]:
    unique = list(dict.fromkeys(user_ids))
    if len(unique) < minimum or len(unique) != len(user_ids) or owner_id in unique:
        raise ApiError(422, "VALIDATION_ERROR", "서로 다른 친구 ID를 입력해 주세요.")
    return unique


def companion_room_id(post_id: str) -> str:
    room_id = "crm_" + post_id[4:]
    if not post_id.startswith("cpo_") or not re.fullmatch(ROOM_ID_PATTERN, room_id):
        raise ValueError("유효한 동행 글 ID가 필요합니다.")
    return room_id


def direct_pair(a: UUID, b: UUID) -> dict:
    low, high = sorted((a, b))
    return {"a": low, "b": high, "key": f"{low}|{high}"}


def _lock_direct_pair(db: Session, pair: dict) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('chat:direct:' || :key, 0))"), pair)


def _check_actor(db: Session, user_id: UUID) -> None:
    if db.scalar(text("SELECT status FROM public.users WHERE user_id = :uid FOR SHARE"),
                 {"uid": user_id}) != "active":
        raise unauthorized()


def _check_friends(db: Session, owner_id: UUID, users: list[UUID], *, direct: bool = False) -> None:
    for user_id in users:
        pair = direct_pair(owner_id, user_id)
        if direct and db.scalar(text("""
            SELECT EXISTS (
                SELECT 1 FROM public.user_blocks WHERE (blocker, blocked) IN ((:a, :b), (:b, :a))
            )
        """), pair):
            raise blocked()
        if not db.scalar(text("""
            SELECT EXISTS (
                SELECT 1 FROM public.friendships f
                JOIN public.users u ON u.user_id = :uid AND u.status = 'active'
                WHERE f.user_a = :a AND f.user_b = :b
                AND NOT EXISTS (
                    SELECT 1 FROM public.user_blocks WHERE (blocker, blocked) IN ((:a, :b), (:b, :a))
                )
            )
        """), {**pair, "uid": user_id}):
            raise not_friends()


def _locked_room(db: Session, room_id: str):
    room = db.execute(text("""
        SELECT room_type, owner_id, status, last_seq, closed_by_block
        FROM public.chat_rooms WHERE room_id = :room FOR UPDATE
    """), {"room": room_id}).one_or_none()
    if room is None:
        raise forbidden()
    return room


def _member_status(db: Session, room_id: str, user_id: UUID) -> str | None:
    return db.scalar(text("""
        SELECT status FROM public.chat_members WHERE room_id = :room AND user_id = :uid
    """), {"room": room_id, "uid": user_id})


def _can_read_direct(db: Session, room_id: str, user_id: UUID, room) -> bool:
    if room.room_type != "direct":
        return True
    return not room.closed_by_block and not db.scalar(text("""
        SELECT EXISTS (
            SELECT 1 FROM public.chat_members peer JOIN public.user_blocks b
              ON (b.blocker, b.blocked) IN ((peer.user_id, :uid), (:uid, peer.user_id))
            WHERE peer.room_id = :room AND peer.user_id <> :uid
        )
    """), {"room": room_id, "uid": user_id})


def _join(db: Session, room_id: str, user_id: UUID, role: str = "member") -> None:
    db.execute(text("""
        INSERT INTO public.chat_members (room_id, user_id, role, status, joined_at, last_read_seq)
        SELECT room_id, :uid, :role, 'joined', statement_timestamp(), last_seq
        FROM public.chat_rooms WHERE room_id = :room
        ON CONFLICT (room_id, user_id) DO UPDATE SET
            role = EXCLUDED.role, status = 'joined', joined_at = EXCLUDED.joined_at,
            last_read_seq = EXCLUDED.last_read_seq, left_at = NULL
        WHERE chat_members.status <> 'joined'
    """), {"room": room_id, "uid": user_id, "role": role})


def _invite(db: Session, room_id: str, owner_id: UUID, users: list[UUID]) -> list[dict]:
    if not users:
        return []
    invited = db.execute(text("""
        INSERT INTO public.chat_members (room_id, user_id, status, invited_by, invited_at)
        SELECT :room, uid, 'invited', :owner, statement_timestamp()
        FROM unnest(CAST(:users AS uuid[])) AS target(uid)
        ON CONFLICT (room_id, user_id) DO UPDATE SET
            status = 'invited', role = 'member', invited_by = EXCLUDED.invited_by,
            invited_at = EXCLUDED.invited_at, joined_at = NULL, left_at = NULL, last_read_seq = 0
        WHERE chat_members.status NOT IN ('invited', 'joined')
        RETURNING user_id, status, invited_at
    """), {"room": room_id, "owner": owner_id, "users": users}).mappings().all()
    if invited:
        db.execute(text("""
            INSERT INTO public.notifications (user_id, type, ref_type, ref_id)
            SELECT uid, 'room_invited', 'chat_room', :room
            FROM unnest(CAST(:users AS uuid[])) AS target(uid)
        """), {"room": room_id, "users": [row["user_id"] for row in invited]})
    return [dict(row) for row in invited]


def _require_owner(db: Session, room, room_id: str, user_id: UUID) -> None:
    if (room.room_type != "friend_group" or room.owner_id != user_id
            or _member_status(db, room_id, user_id) != "joined"):
        raise forbidden()


class ChatRooms:
    """동행·친구 호출부에서 db를 전달하면 해당 서비스 트랜잭션을 함께 쓴다."""

    @staticmethod
    def create_companion_room(post_id: str, owner_id: UUID, *, db: Session | None = None) -> str:
        room_id = companion_room_id(post_id)
        with (nullcontext(db) if db is not None else service_db_session()) as tx:
            _check_actor(tx, owner_id)
            tx.execute(text("""
                INSERT INTO public.chat_rooms (room_id, room_type, owner_id)
                VALUES (:room, 'companion', :owner) ON CONFLICT (room_id) DO NOTHING
            """), {"room": room_id, "owner": owner_id})
            room = _locked_room(tx, room_id)
            if room.room_type != "companion" or room.owner_id != owner_id:
                raise invalid_state()
            if room.status == "active":
                _join(tx, room_id, owner_id, "owner")
        return room_id

    @staticmethod
    def add_member(room_id: str, user_id: UUID, *, db: Session | None = None) -> None:
        with (nullcontext(db) if db is not None else service_db_session()) as tx:
            _check_actor(tx, user_id)
            room = _locked_room(tx, room_id)
            if room.room_type != "companion" or room.status != "active":
                raise invalid_state()
            _join(tx, room_id, user_id)

    @staticmethod
    def close_direct_room_on_unblock(user_a: UUID, user_b: UUID, *, db: Session | None = None) -> None:
        pair = direct_pair(user_a, user_b)
        with (nullcontext(db) if db is not None else service_db_session()) as tx:
            _lock_direct_pair(tx, pair)
            # The 019 DELETE trigger handles calls made after the block row is gone.
            tx.execute(text("""
                UPDATE public.chat_rooms SET status = 'closed', closed_by_block = true
                WHERE direct_key = :key AND status <> 'closed' AND EXISTS (
                    SELECT 1 FROM public.user_blocks WHERE (blocker, blocked) IN ((:a, :b), (:b, :a))
                )
            """), pair)

    @staticmethod
    def create(user_id: UUID, request: DirectRoom | GroupRoom) -> tuple[str, bool]:
        with service_db_session() as db:
            _check_actor(db, user_id)
            if isinstance(request, DirectRoom):
                invitees([request.friend_id], user_id)
                pair = direct_pair(user_id, request.friend_id)
                _lock_direct_pair(db, pair)
                _check_friends(db, user_id, [request.friend_id], direct=True)
                existing = db.scalar(text("""
                    SELECT room_id FROM public.chat_rooms
                    WHERE direct_key = :key AND status <> 'closed' FOR UPDATE
                """), pair)
                if existing:
                    return existing, False
                room_id = f"crm_{ULID()}"
                db.execute(text("""
                    INSERT INTO public.chat_rooms (room_id, room_type, direct_key)
                    VALUES (:room, 'direct', :key)
                """), {"room": room_id, **pair})
                _join(db, room_id, user_id)
                _join(db, room_id, request.friend_id)
                return room_id, True

            users = invitees(request.invitee_ids, user_id, minimum=2)
            _check_friends(db, user_id, users)
            room_id = f"crm_{ULID()}"
            db.execute(text("""
                INSERT INTO public.chat_rooms (room_id, room_type, name, owner_id)
                VALUES (:room, 'friend_group', :name, :owner)
            """), {"room": room_id, "name": request.name, "owner": user_id})
            _join(db, room_id, user_id, "owner")
            _invite(db, room_id, user_id, users)
            return room_id, True

    @staticmethod
    def invite(user_id: UUID, room_id: str, target_ids: list[UUID]) -> list[dict]:
        with service_db_session() as db:
            _check_actor(db, user_id)
            room = _locked_room(db, room_id)
            _require_owner(db, room, room_id, user_id)
            if room.status != "active":
                raise invalid_state()
            users = invitees(target_ids, user_id, minimum=0)
            current = set(db.scalars(text("""
                SELECT user_id FROM public.chat_members WHERE room_id = :room AND status IN ('invited', 'joined')
            """), {"room": room_id}))
            pending = [target for target in users if target not in current]
            _check_friends(db, user_id, pending)
            return _invite(db, room_id, user_id, pending)

    @staticmethod
    def act(user_id: UUID, room_id: str, action: Action) -> tuple[str, str]:
        with service_db_session() as db:
            _check_actor(db, user_id)
            room = _locked_room(db, room_id)
            status = _member_status(db, room_id, user_id)
            if status is None or room.room_type == "companion":
                raise forbidden()
            if action == "accept" and status == "invited" and room.status == "active":
                _join(db, room_id, user_id)
                return "joined", room.status
            if action == "decline" and status == "invited":
                db.execute(text("""
                    UPDATE public.chat_members SET status = 'declined' WHERE room_id = :room AND user_id = :uid
                """), {"room": room_id, "uid": user_id})
                return "declined", room.status
            if action != "leave" or status != "joined":
                raise invalid_state()

            db.execute(text("""
                UPDATE public.chat_members SET status = 'left', left_at = statement_timestamp(), role = 'member'
                WHERE room_id = :room AND user_id = :uid
            """), {"room": room_id, "uid": user_id})
            new_status = room.status
            if room.room_type == "direct":
                new_status = "closed"
                db.execute(text("UPDATE public.chat_rooms SET status = 'closed' WHERE room_id = :room"),
                           {"room": room_id})
            elif room.owner_id == user_id:
                successor = db.scalar(text("""
                    SELECT m.user_id FROM public.chat_members m JOIN public.users u USING (user_id)
                    WHERE m.room_id = :room AND m.status = 'joined' AND u.status = 'active'
                    ORDER BY m.joined_at, m.user_id LIMIT 1
                """), {"room": room_id})
                new_status = room.status if successor else "closed"
                db.execute(text("""
                    UPDATE public.chat_rooms SET owner_id = :owner, status = :status WHERE room_id = :room
                """), {"room": room_id, "owner": successor, "status": new_status})
                if successor:
                    db.execute(text("""
                        UPDATE public.chat_members SET role = 'owner' WHERE room_id = :room AND user_id = :owner
                    """), {"room": room_id, "owner": successor})
            return "left", new_status

    @staticmethod
    def rename(user_id: UUID, room_id: str, name: str) -> None:
        with service_db_session() as db:
            _check_actor(db, user_id)
            room = _locked_room(db, room_id)
            _require_owner(db, room, room_id, user_id)
            if room.status != "active":
                raise forbidden()
            db.execute(text("UPDATE public.chat_rooms SET name = :name WHERE room_id = :room"),
                       {"name": name, "room": room_id})

    @staticmethod
    def read(user_id: UUID, room_id: str, seq: int) -> None:
        with service_db_session() as db:
            _check_actor(db, user_id)
            room = _locked_room(db, room_id)
            if _member_status(db, room_id, user_id) != "joined" or not _can_read_direct(db, room_id, user_id, room):
                raise forbidden()
            db.execute(text("""
                UPDATE public.chat_members SET last_read_seq = GREATEST(last_read_seq, LEAST(:seq, :last_seq))
                WHERE room_id = :room AND user_id = :uid
            """), {"room": room_id, "uid": user_id, "seq": seq, "last_seq": room.last_seq})

    @staticmethod
    def send(user_id: UUID, room_id: str, client_id: str, body: str, charge) -> tuple[int, int, bool]:
        with service_db_session() as db:
            _check_actor(db, user_id)
            room = _locked_room(db, room_id)
            if _member_status(db, room_id, user_id) != "joined" or not _can_read_direct(db, room_id, user_id, room):
                raise forbidden()
            params = {"room": room_id, "uid": user_id, "id": client_id, "body": body}
            existing = db.execute(text("""
                SELECT message_id, seq FROM public.chat_messages
                WHERE room_id = :room AND sender_id = :uid AND client_message_id = :id
            """), params).one_or_none()
            if existing:
                return existing.message_id, existing.seq, False
            if room.status != "active":
                raise read_only()
            charge(user_id, room_id)
            seq = db.scalar(text("""
                UPDATE public.chat_rooms SET last_seq = last_seq + 1 WHERE room_id = :room RETURNING last_seq
            """), params)
            message_id = db.scalar(text("""
                INSERT INTO public.chat_messages (room_id, seq, sender_id, msg_type, body, client_message_id, created_at)
                VALUES (:room, :seq, :uid, 'text', :body, :id, statement_timestamp()) RETURNING message_id
            """), {**params, "seq": seq})
            return message_id, seq, True


async def room_access(db: AsyncSession, user_id: UUID, room_id: str) -> tuple[str, str | None]:
    row = (await db.execute(text("""
        SELECT r.status, m.status AS member_status, public.app_chat_can_read(r.room_id) AS allowed
        FROM public.chat_members m LEFT JOIN public.chat_rooms r USING (room_id)
        WHERE m.room_id = :room AND m.user_id = :uid
    """), {"room": room_id, "uid": user_id})).one_or_none()
    if row is None:
        return "closed", "removed"
    if row.member_status != "joined":
        return row.status or "closed", "left" if row.member_status == "left" else "removed"
    return row.status, None if row.allowed else "blocked"


async def messages(
    db: AsyncSession, room_id: str, after: int | None, before: int | None, limit: int,
) -> tuple[list[dict], bool]:
    # Order and predicates are selected from fixed SQL. Params carry user input.
    direction = "ASC" if after is not None else "DESC"
    conditions = []
    if after is not None:
        conditions.append("AND seq > :after")
    if before is not None:
        conditions.append("AND seq < :before")
    rows = (await db.execute(text(f"""
        SELECT message_id, seq, sender_id, public.app_public_display_name(sender_id) AS sender_display_name,
               msg_type, body, created_at
        FROM public.chat_messages WHERE room_id = :room {" ".join(conditions)}
        ORDER BY seq {direction} LIMIT :limit
    """), {"room": room_id, "after": after, "before": before, "limit": limit + 1})).mappings().all()
    page = rows[:limit]
    if direction == "DESC":
        page.reverse()
    return [dict(row) for row in page], len(rows) > limit


async def list_rooms(db: AsyncSession, user_id: UUID, selected: RoomFilter) -> list[dict]:
    rows = (await db.execute(text("""
        SELECT r.room_id, r.room_type, r.name, r.status, stats.last_message_at,
               stats.unread_count, m.status AS my_status
        FROM public.chat_rooms r JOIN public.chat_members m USING (room_id)
        CROSS JOIN LATERAL (
            SELECT max(c.created_at) AS last_message_at, count(*) FILTER (WHERE c.seq > m.last_read_seq AND c.sender_id IS DISTINCT FROM :uid) AS unread_count
            FROM public.chat_messages c WHERE c.room_id = r.room_id
        ) stats
        WHERE m.user_id = :uid AND m.status IN ('invited','joined') AND CASE :selected
            WHEN 'all' THEN true WHEN 'past' THEN r.status <> 'active'
            WHEN 'companion' THEN r.room_type = 'companion' ELSE r.room_type <> 'companion'
        END
        ORDER BY stats.last_message_at DESC NULLS LAST, r.created_at DESC, r.room_id
    """), {"uid": user_id, "selected": selected})).mappings().all()
    return [dict(row) for row in rows]


_NOTIFICATION_TTL = "created_at > statement_timestamp() - interval '2160 hours'"


async def notifications(db: AsyncSession, unread_only: bool, page: int) -> dict:
    rows = (await db.execute(text(f"""
        SELECT notification_id, type, ref_type, ref_id, created_at, read_at
        FROM public.notifications WHERE {_NOTIFICATION_TTL} AND (NOT :unread OR read_at IS NULL)
        ORDER BY created_at DESC, notification_id DESC LIMIT :limit OFFSET :offset
    """), {"unread": unread_only, "limit": PAGE_SIZE, "offset": (page - 1) * PAGE_SIZE})).mappings().all()
    count = await db.scalar(text(f"""
        SELECT count(*) FROM public.notifications WHERE {_NOTIFICATION_TTL} AND read_at IS NULL
    """))
    return {"items": [dict(row) for row in rows], "unread_count": count}


async def read_notifications(db: AsyncSession, ids: list[int] | None) -> None:
    await db.execute(text(f"""
        UPDATE public.notifications SET read_at = statement_timestamp()
        WHERE {_NOTIFICATION_TTL} AND read_at IS NULL
          AND (:all_rows OR notification_id = ANY(CAST(:ids AS bigint[])))
    """), {"all_rows": ids is None, "ids": ids or []})


async def notification_head(db: AsyncSession) -> int:
    return await db.scalar(text("SELECT COALESCE(max(notification_id), 0) FROM public.notifications"))


async def recent_notifications(db: AsyncSession, after: int) -> list[dict]:
    rows = (await db.execute(text(f"""
        SELECT notification_id, type, ref_type, ref_id, created_at
        FROM public.notifications WHERE {_NOTIFICATION_TTL} AND notification_id > :after
        ORDER BY notification_id LIMIT 100
    """), {"after": after})).mappings().all()
    return [dict(row) for row in rows]
