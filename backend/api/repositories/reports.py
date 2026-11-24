from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from ulid import ULID

from api.auth.tokens import unauthorized
from api.schemas import reports as schema
from api.services import reports as rules
from shared.db.session import service_db_session

_SUMMARY_FIELDS = "report_id, target_type, target_id, reason, status, created_at"
_CHAT_TYPES = ("chat_message", "chat_room")


async def visible_target_room(db: AsyncSession, kind: schema.TargetType, target: str) -> str | None:
    if kind == "chat_message":
        room = await db.scalar(text("""
            SELECT room_id FROM public.chat_messages WHERE message_id = :id
        """), {"id": int(target)})
        if room is None:
            raise rules.target_not_found()
        return room
    if kind == "chat_room":
        joined = await db.scalar(text("SELECT public.app_room_joined_at(:id) IS NOT NULL"), {"id": target})
        if not joined:
            raise rules.target_not_found()
        return target
    if kind == "companion_post":
        visible = await db.scalar(text("SELECT 1 FROM public.companion_posts WHERE post_id = :id"), {"id": target})
        if not visible:
            raise rules.target_not_found()
    return None


def submit(actor: UUID, request: schema.ReportCreate, target: str, room: str | None) -> schema.ReportCreated:
    with service_db_session() as db:
        if db.scalar(text("SELECT status FROM public.users WHERE user_id = :uid FOR SHARE"),
                     {"uid": actor}) != "active":
            raise unauthorized()
        params = {"actor": actor, "kind": request.target_type, "target": target,
                  "reason": request.reason, "detail": request.detail, "report_id": f"rpt_{ULID()}"}
        # After taking this lock, concurrent submissions see the committed winner.
        db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                   {"key": f"report:{actor}:{request.target_type}:{target}"})
        if room is not None:
            joined = db.scalar(text("""
                SELECT 1 FROM public.chat_members
                WHERE room_id = :room AND user_id = :actor AND status = 'joined' FOR SHARE
            """), {"room": room, "actor": actor})
            if not joined:
                raise rules.target_not_found()
        elif request.target_type == "user":
            active = db.scalar(text("""
                SELECT 1 FROM public.users WHERE user_id = :uid AND status = 'active'
            """), {"uid": UUID(target)})
            if not active:
                raise rules.target_not_found()
        report_id = db.scalar(text("""
            WITH day AS (SELECT date_trunc('day', statement_timestamp(), 'Asia/Seoul') AS start_at)
            INSERT INTO public.reports (report_id, reporter_id, target_type, target_id, reason, detail, created_at)
            SELECT :report_id, :actor, :kind, :target, :reason, :detail, statement_timestamp()
            FROM day WHERE NOT EXISTS (
                SELECT 1 FROM public.reports
                WHERE reporter_id = :actor AND target_type = :kind AND target_id = :target
                  AND created_at >= day.start_at AND created_at < day.start_at + interval '24 hours'
            )
            RETURNING report_id
        """), params)
        if report_id is None:
            raise rules.duplicate_report()
        return schema.ReportCreated(report_id=report_id)


def _locked_report(db: Session, report_id: str) -> schema.ReportSummary:
    row = db.execute(text(f"""
        SELECT {_SUMMARY_FIELDS} FROM public.reports WHERE report_id = :id FOR UPDATE
    """), {"id": report_id}).mappings().one_or_none()
    if row is None:
        raise rules.report_not_found()
    return schema.ReportSummary.model_validate(row)


def _start_review(db: Session, report: schema.ReportSummary) -> None:
    if report.status == "received":
        db.execute(text("UPDATE public.reports SET status = 'reviewing' WHERE report_id = :id"),
                   {"id": report.report_id})
        report.status = "reviewing"


def _message_id(target: str) -> int:
    # Invalid historical targets are treated as unavailable evidence.
    if not target.isascii() or not target.isdecimal() or len(target) > 19 or not 0 < int(target) <= 2**63 - 1:
        raise rules.target_not_found()
    return int(target)


def _chat_detail(db: Session, admin_id: UUID, report: schema.ReportSummary) -> schema.ReportDetail:
    message_id = _message_id(report.target_id) if report.target_type == "chat_message" else None
    room_id = report.target_id
    if message_id is not None:
        room_id = db.scalar(text("SELECT room_id FROM public.chat_messages WHERE message_id = :id"),
                            {"id": message_id})
        if room_id is None:
            raise rules.target_not_found()

    # Resolve only the room ID above. Record this access before loading any evidence.
    access_id = db.scalar(text("""
        INSERT INTO public.chat_admin_access (admin_id, room_id, report_id, reason)
        SELECT :admin, room_id, :report, :reason FROM public.chat_rooms WHERE room_id = :room
        RETURNING access_id
    """), {"admin": admin_id, "room": room_id, "report": report.report_id, "reason": report.reason})
    if access_id is None:
        raise rules.target_not_found()

    room = db.execute(text("""
        SELECT room_id, room_type, name, status FROM public.chat_rooms WHERE room_id = :room
    """), {"room": room_id}).mappings().one()
    message = None
    if message_id is not None:
        row = db.execute(text("""
            SELECT m.message_id, m.seq, m.sender_id, m.created_at, CASE
                WHEN r.room_type = 'companion' AND (
                    r.read_only_at IS NULL OR r.read_only_at > statement_timestamp() - interval '72 hours'
                ) THEN m.body
                WHEN r.room_type <> 'companion' AND m.created_at > statement_timestamp() - interval '720 hours'
                THEN m.body
            END AS body
            FROM public.chat_messages m JOIN public.chat_rooms r USING (room_id)
            WHERE m.message_id = :id AND m.room_id = :room
        """), {"id": message_id, "room": room_id}).mappings().one_or_none()
        if row is None:
            raise rules.target_not_found()
        message = schema.ReportMessage.model_validate(row)
    return schema.ReportDetail(report=report, room=schema.ReportRoom.model_validate(room),
                               message=message, access_id=access_id)


def _apply_action(db: Session, target: str, action: schema.ReportAction, admin_id: UUID) -> None:
    if action == "dismiss":
        return
    if action == "hide_message":
        result = db.execute(text("""
            UPDATE public.chat_messages SET deleted_at = COALESCE(deleted_at, statement_timestamp())
            WHERE message_id = :id
        """), {"id": _message_id(target)})
    elif action == "hide_post":
        result = db.execute(text("""
            UPDATE public.companion_posts
            SET hidden_at = COALESCE(hidden_at, statement_timestamp()), hidden_by = COALESCE(hidden_by, :admin)
            WHERE post_id = :id
        """), {"id": target, "admin": admin_id})
    elif action == "close_room":
        result = db.execute(text("""
            UPDATE public.chat_rooms
            SET status = 'read_only', read_only_at = COALESCE(read_only_at, statement_timestamp())
            WHERE room_id = :id AND status IN ('active', 'read_only')
        """), {"id": target})
    else:
        try:
            user_id = UUID(target)
        except ValueError:
            raise rules.target_not_found() from None
        result = db.execute(text("""
            UPDATE public.users SET status = 'disabled' WHERE user_id = :id AND status <> 'deleted'
        """), {"id": user_id})
    if result.rowcount != 1:
        raise rules.target_not_found()


class PostgresReports:
    def list(self, status: schema.ReportStatus | None, page: int) -> schema.ReportPage:
        with service_db_session() as db:
            rows = db.execute(text(f"""
                SELECT {_SUMMARY_FIELDS} FROM public.reports
                WHERE (CAST(:status AS text) IS NULL OR status = :status)
                ORDER BY created_at DESC, report_id DESC LIMIT :size OFFSET :offset
            """), {"status": status, "size": rules.PAGE_SIZE, "offset": (page - 1) * rules.PAGE_SIZE}).mappings()
            return schema.ReportPage(items=[schema.ReportSummary.model_validate(row) for row in rows], page=page)

    def detail(self, admin_id: UUID, report_id: str) -> schema.ReportDetail:
        with service_db_session() as db:
            report = _locked_report(db, report_id)
            _start_review(db, report)
            if report.target_type in _CHAT_TYPES:
                return _chat_detail(db, admin_id, report)
            return schema.ReportDetail(report=report, room=None, message=None, access_id=None)

    def decide(self, admin_id: UUID, decision: schema.ReportDecision) -> schema.ReportResult:
        with service_db_session() as db:
            report = _locked_report(db, decision.report_id)
            rules.check_decision(report.status, report.target_type, decision.action)
            _start_review(db, report)
            _apply_action(db, report.target_id, decision.action, admin_id)
            result = db.execute(text("""
                UPDATE public.reports
                SET status = :status, handled_by = :admin, handled_at = statement_timestamp()
                WHERE report_id = :id RETURNING report_id, status, handled_by, handled_at
            """), {"status": "dismissed" if decision.action == "dismiss" else "actioned",
                   "admin": admin_id, "id": decision.report_id}).mappings().one()
            db.execute(text("""
                INSERT INTO public.report_moderation (report_id, action, note) VALUES (:id, :action, :note)
            """), {"id": decision.report_id, "action": decision.action, "note": decision.note})
            return schema.ReportResult.model_validate(result)
