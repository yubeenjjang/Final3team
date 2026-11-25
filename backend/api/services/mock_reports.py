from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import UUID

from ulid import ULID

from api.mocks import store
from api.routers.community import companions
from api.schemas import reports as schema
from api.services import mock_chat, reports as rules
from api.services.mock_auth import disable_account


@dataclass(frozen=True)
class StoredReport:
    summary: schema.ReportSummary
    reporter_id: UUID
    detail: str | None


@dataclass(frozen=True)
class ChatAccess:
    admin_id: UUID
    room_id: str
    report_id: str
    reason: schema.ReportReason
    created_at: datetime


def now() -> datetime:
    return datetime.now(timezone.utc)


def _chat_target(kind: schema.TargetType, target: str) -> tuple[str, mock_chat.Room, dict | None]:
    rooms = mock_chat.mock_rooms.rooms
    if kind == "chat_room" and target in rooms:
        return target, rooms[target], None
    if kind == "chat_message":
        for room_id, room in rooms.items():
            for message in room.messages:
                if str(message["message_id"]) == target:
                    return room_id, room, message
    raise rules.target_not_found()


def _assert_target(actor: UUID, kind: schema.TargetType, target: str) -> None:
    if kind in ("chat_room", "chat_message"):
        with mock_chat.mock_rooms.lock:
            room_id, room, message = _chat_target(kind, target)
            member = room.members.get(actor)
            if member is None or member.status != "joined":
                raise rules.target_not_found()
            if message is not None and message not in mock_chat.mock_rooms._visible(room_id, actor):
                raise rules.target_not_found()
    elif kind == "companion_post":
        with companions.memory.lock:
            post = companions.memory.posts.get(target)
            if post is None or (post.hidden and post.author_id != str(actor)):
                raise rules.target_not_found()
    else:
        with store.auth_lock:
            if not any(user.user_id == target and not user.disabled for user in store.users_by_email.values()):
                raise rules.target_not_found()


def _apply_action(kind: schema.TargetType, target: str, action: schema.ReportAction) -> None:
    if action == "dismiss":
        return
    if action == "block_user":
        if not disable_account(target):
            raise rules.target_not_found()
    elif action == "hide_post":
        with companions.memory.lock:
            post = companions.memory.posts.get(target)
            if post is None:
                raise rules.target_not_found()
            post.hidden = True
    else:
        with mock_chat.mock_rooms.lock:
            _, room, message = _chat_target(kind, target)
            if action == "hide_message":
                assert message is not None
                message.setdefault("deleted_at", now())
            elif room.status == "closed":
                raise rules.target_not_found()
            else:
                room.status = "read_only"
                room.read_only_at = room.read_only_at or now()


class MemoryReports:
    def __init__(self) -> None:
        self._lock = Lock()
        self._reports: dict[str, StoredReport] = {}
        self._duplicate_keys: set[tuple[UUID, str, str]] = set()
        self._day = None
        self._access: list[ChatAccess] = []
        self._decisions: dict[str, tuple[schema.ReportDecision, schema.ReportResult]] = {}

    def submit(self, actor: UUID, request: schema.ReportCreate, target: str) -> schema.ReportCreated:
        with self._lock:
            _assert_target(actor, request.target_type, target)
            timestamp = now()
            day = timestamp.astimezone(rules.KST).date()
            if self._day != day:
                self._duplicate_keys.clear()
                self._day = day
            key = actor, request.target_type, target
            if key in self._duplicate_keys:
                raise rules.duplicate_report()
            report_id = f"rpt_{ULID()}"
            summary = schema.ReportSummary(
                report_id=report_id, target_type=request.target_type, target_id=target,
                reason=request.reason, status="received", created_at=timestamp,
            )
            self._reports[report_id] = StoredReport(summary, actor, request.detail)
            self._duplicate_keys.add(key)
            return schema.ReportCreated(report_id=report_id)

    def _report(self, report_id: str) -> schema.ReportSummary:
        if report_id not in self._reports:
            raise rules.report_not_found()
        return self._reports[report_id].summary

    def list(self, status: schema.ReportStatus | None, page: int) -> schema.ReportPage:
        with self._lock:
            summaries = (record.summary for record in self._reports.values())
            items = sorted(summaries, key=lambda r: (r.created_at, r.report_id), reverse=True)
            selected = [item for item in items if status is None or item.status == status]
            offset = (page - 1) * rules.PAGE_SIZE
            return schema.ReportPage(
                items=[item.model_copy() for item in selected[offset:offset + rules.PAGE_SIZE]], page=page,
            )

    def detail(self, admin_id: UUID, report_id: str) -> schema.ReportDetail:
        with self._lock:
            report = self._report(report_id)
            room_view = None
            message_view = None
            access_id = None
            if report.target_type in ("chat_room", "chat_message"):
                with mock_chat.mock_rooms.lock:
                    room_id, room, message = _chat_target(report.target_type, report.target_id)
                    timestamp = now()
                    self._access.append(ChatAccess(admin_id, room_id, report_id, report.reason, timestamp))
                    access_id = len(self._access)
                    room_view = schema.ReportRoom(room_id=room_id, room_type=room.room_type,
                                                  name=room.name, status=room.status)
                    if message is not None:
                        expired = (
                            room.read_only_at is not None and room.read_only_at <= timestamp - timedelta(days=3)
                            if room.room_type == "companion"
                            else message["created_at"] <= timestamp - timedelta(days=30)
                        )
                        message_view = schema.ReportMessage.model_validate(
                            dict(message, body=None if expired else message["body"]),
                        )
            if report.status == "received":
                report.status = "reviewing"
            return schema.ReportDetail(report=report.model_copy(), room=room_view,
                                       message=message_view, access_id=access_id)

    def decide(self, admin_id: UUID, decision: schema.ReportDecision) -> schema.ReportResult:
        with self._lock:
            report = self._report(decision.report_id)
            rules.check_decision(report.status, report.target_type, decision.action)
            _apply_action(report.target_type, report.target_id, decision.action)
            if report.status == "received":
                report.status = "reviewing"
            report.status = "dismissed" if decision.action == "dismiss" else "actioned"
            result = schema.ReportResult(report_id=report.report_id, status=report.status,
                                         handled_by=admin_id, handled_at=now())
            self._decisions[report.report_id] = decision, result
            return result


mock_reports = MemoryReports()
