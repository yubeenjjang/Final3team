import logging
from time import time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.auth.state import AuthStateUnavailable, get_auth_state
from api.auth.tokens import AccessClaims, password_matches, unauthorized
from api.errors import ApiError
from shared.db.session import service_db_session

_logger = logging.getLogger(__name__)


def password_mismatch() -> ApiError:
    return ApiError(403, "PASSWORD_MISMATCH", "비밀번호를 다시 확인해 주세요.")


def delete_account(claims: AccessClaims, password: str) -> None:
    # These tables deliberately have no application-role write grants for cross-user changes.
    owner = {"uid": claims.user_id}
    with service_db_session() as db:
        account = db.execute(text("""
            SELECT status, password_hash FROM public.users WHERE user_id = :uid FOR NO KEY UPDATE
        """), owner).one_or_none()
        if account is None or account.status != "active":
            raise unauthorized()
        if not password_matches(password, account.password_hash):
            raise password_mismatch()

        for table in ("refresh_tokens", "favorites", "user_festival_preferences", "notifications"):
            db.execute(text(f"DELETE FROM public.{table} WHERE user_id = :uid"), owner)
        cancelled_rooms = _cancel_companion_activity(db, owner)
        db.execute(text("DELETE FROM public.friendships WHERE user_a = :uid OR user_b = :uid"), owner)
        db.execute(text("DELETE FROM public.friend_requests WHERE from_user = :uid OR to_user = :uid"), owner)
        db.execute(text("DELETE FROM public.user_blocks WHERE blocker = :uid OR blocked = :uid"), owner)
        _leave_chat_rooms(db, owner, cancelled_rooms)
        _purge_assistant_content(db, owner)
        db.execute(text("""
            UPDATE public.profiles SET display_name = NULL, birth_year = NULL, gender = NULL
            WHERE user_id = :uid
        """), owner)
        db.execute(text("""
            UPDATE public.users
            SET email = 'deleted+' || CAST(:uid AS text) || '@invalid', password_hash = '!', status = 'deleted'
            WHERE user_id = :uid
        """), owner)

    ttl = claims.expires_at - int(time())
    if ttl > 0:
        try:
            get_auth_state().revoke(claims.jti, ttl)
        except AuthStateUnavailable:
            # The committed account status already invalidates every access token.
            _logger.warning("Account deleted while the token revocation store was unavailable.")


def _cancel_companion_activity(db: Session, owner: dict[str, UUID]) -> list[str]:
    db.execute(text("""
        SELECT p.post_id FROM public.companion_posts p
        WHERE p.status IN ('open', 'full') AND (
            p.author_id = :uid OR EXISTS (
                SELECT 1 FROM public.companion_applications a
                WHERE a.post_id = p.post_id AND a.applicant_id = :uid
                  AND a.status IN ('pending', 'approved')
            )
        ) ORDER BY p.post_id FOR UPDATE OF p
    """), owner)
    cancelled = db.execute(text("""
        UPDATE public.companion_posts SET status = 'cancelled', ended_at = now()
        WHERE author_id = :uid AND status IN ('open', 'full')
        RETURNING post_id, room_id
    """), owner).all()
    # Other authors can fill the seat vacated by an approved applicant.
    db.execute(text("""
        UPDATE public.companion_posts p SET approved_count = GREATEST(0, p.approved_count - 1), status = 'open'
        FROM public.companion_applications a
        WHERE a.post_id = p.post_id AND a.applicant_id = :uid AND a.status = 'approved'
          AND p.status IN ('open', 'full')
    """), owner)
    db.execute(text("""
        UPDATE public.companion_applications a SET status = 'cancelled', decided_at = now()
        FROM public.companion_posts p
        WHERE a.post_id = p.post_id AND a.status IN ('pending', 'approved') AND (
            p.post_id = ANY(CAST(:cancelled_posts AS text[]))
            OR (a.applicant_id = :uid AND p.status IN ('open', 'full'))
        )
    """), {**owner, "cancelled_posts": [row.post_id for row in cancelled]})
    return [row.room_id for row in cancelled]


def _leave_chat_rooms(db: Session, owner: dict[str, UUID], cancelled_rooms: list[str]) -> None:
    db.execute(text("""
        SELECT r.room_id FROM public.chat_rooms r
        WHERE r.owner_id = :uid OR r.room_id = ANY(CAST(:cancelled_rooms AS text[])) OR EXISTS (
            SELECT 1 FROM public.chat_members m
            WHERE m.room_id = r.room_id AND m.user_id = :uid AND m.status IN ('invited', 'joined')
        ) ORDER BY r.room_id FOR UPDATE OF r
    """), {**owner, "cancelled_rooms": cancelled_rooms})
    # Close the cancelled posts to new messages and start their three-day retention period.
    db.execute(text("""
        UPDATE public.chat_rooms SET status = 'read_only', read_only_at = now()
        WHERE room_id = ANY(CAST(:cancelled_rooms AS text[])) AND status = 'active'
    """), {"cancelled_rooms": cancelled_rooms})
    left_rooms = db.scalars(text("""
        UPDATE public.chat_members SET status = 'left', role = 'member', left_at = now()
        WHERE user_id = :uid AND status IN ('invited', 'joined') RETURNING room_id
    """), owner).all()
    db.execute(text("""
        UPDATE public.chat_rooms SET status = 'closed'
        WHERE room_id = ANY(CAST(:left_rooms AS text[])) AND room_type = 'direct'
    """), {"left_rooms": left_rooms})
    db.execute(text("""
        WITH successors AS (
            SELECT r.room_id, next_member.user_id
            FROM public.chat_rooms r LEFT JOIN LATERAL (
                SELECT m.user_id FROM public.chat_members m
                JOIN public.users u ON u.user_id = m.user_id AND u.status = 'active'
                WHERE m.room_id = r.room_id AND m.status = 'joined' AND m.user_id <> :uid
                ORDER BY m.joined_at, m.user_id LIMIT 1
            ) next_member ON true
            WHERE r.owner_id = :uid
        ), updated_rooms AS (
            UPDATE public.chat_rooms r SET owner_id = s.user_id,
                status = CASE WHEN s.user_id IS NULL AND r.status = 'active' THEN 'closed' ELSE r.status END
            FROM successors s WHERE r.room_id = s.room_id
            RETURNING r.room_id, r.owner_id
        )
        UPDATE public.chat_members m SET role = 'owner' FROM updated_rooms r
        WHERE m.room_id = r.room_id AND m.user_id = r.owner_id
    """), owner)


def _purge_assistant_content(db: Session, owner: dict[str, UUID]) -> None:
    # The checkpointer creates these tables when it is installed in this database.
    for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
        relation = f"langgraph.{table}"
        if db.scalar(text("SELECT to_regclass(:relation) IS NOT NULL"), {"relation": relation}):
            db.execute(text(f"""
                DELETE FROM {relation} WHERE thread_id IN (
                    SELECT own.conversation_id FROM public.assistant_runs own
                    WHERE own.user_id = :uid AND NOT EXISTS (
                        SELECT 1 FROM public.assistant_runs other
                        WHERE other.conversation_id = own.conversation_id AND other.user_id <> :uid
                    )
                )
            """), owner)
    db.execute(text("""
        UPDATE public.assistant_runs SET message = NULL, answer = NULL, result = NULL,
            purged_at = COALESCE(purged_at, now())
        WHERE user_id = :uid
    """), owner)
