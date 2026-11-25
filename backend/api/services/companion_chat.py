"""채팅 작업의 ChatRooms 연동 지점. 호출자가 서비스 트랜잭션을 소유합니다."""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from ulid import ULID


class ChatRooms:
    @staticmethod
    def create_companion_room(db: Session, owner_id: UUID) -> str:
        room_id = "crm_" + str(ULID())
        db.execute(text("""
            INSERT INTO public.chat_rooms (room_id, room_type, owner_id)
            VALUES (:room_id, 'companion', :owner_id)
        """), {"room_id": room_id, "owner_id": owner_id})
        return room_id

    @staticmethod
    def add_member(db: Session, room_id: str, user_id: UUID, *, role: str = "member") -> None:
        db.execute(text("""
            WITH room AS (
                SELECT room_id, last_seq FROM public.chat_rooms WHERE room_id = :room_id FOR UPDATE
            )
            INSERT INTO public.chat_members (room_id, user_id, role, status, joined_at, last_read_seq)
            SELECT room_id, :user_id, :role, 'joined', clock_timestamp(), last_seq FROM room
        """), {"room_id": room_id, "user_id": user_id, "role": role})


def append_system_message(db: Session, room_id: str, body: str) -> None:
    db.execute(text("""
        WITH room AS (
            UPDATE public.chat_rooms SET last_seq = last_seq + 1 WHERE room_id = :room_id
            RETURNING room_id, last_seq
        )
        INSERT INTO public.chat_messages (room_id, seq, msg_type, body, created_at)
        SELECT room_id, last_seq, 'system', :body, clock_timestamp() FROM room
    """), {"room_id": room_id, "body": body})
