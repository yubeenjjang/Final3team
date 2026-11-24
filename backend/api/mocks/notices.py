from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from threading import Lock
from uuid import UUID

from api.schemas.festival_info import Notice, NoticeType
from api.schemas.notices import NoticeCreate, NoticeUpdate
from api.services.festival_lookup import find_festival
from api.services.notices import (
    Action, ControlSnapshot, NoticeRecord, active_at, apply_change, control_version,
    festival_not_found, new_record, notice_not_found, now_kst,
)


NOTICES = {
    "fst_000001": (
        Notice(
            notice_id="ntc_000001",
            type="traffic_control",
            title="세종대로 일부 차로 통제",
            content="축제 기간 세종대로 일부 차로를 통제합니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-20T18:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-12-31T23:00:00+09:00"),
            source="seoul_topis",
            published_at=datetime.fromisoformat("2026-11-20T09:00:00+09:00"),
            control_version="ctl-0001",
        ),
        Notice(
            notice_id="ntc_000002",
            type="operation",
            title="점등 시간 18:00~23:00 안내",
            content="축제 조명은 매일 18시부터 23시까지 켜집니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-20T00:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-12-31T23:59:00+09:00"),
            source="operator",
            published_at=datetime.fromisoformat("2026-11-19T12:00:00+09:00"),
        ),
        Notice(
            notice_id="ntc_000003",
            type="bus_detour",
            title="지난 우회 운행 안내(종료)",
            content="임시 버스 우회 운행이 종료되었습니다.(모의)",
            effective_from=datetime.fromisoformat("2026-11-01T00:00:00+09:00"),
            effective_to=datetime.fromisoformat("2026-11-10T23:59:00+09:00"),
            source="operator",
            published_at=datetime.fromisoformat("2026-10-31T12:00:00+09:00"),
        ),
    ),
}


class MemoryNoticeStore:
    def __init__(self, clock: Callable[[], datetime] = now_kst) -> None:
        self._clock = clock
        self._lock = Lock()
        self._records: dict[str, NoticeRecord] = {}
        self._changes: dict[str, list[tuple[str | None, datetime]]] = {}
        self.events: list[tuple[Action, UUID, NoticeRecord | None, NoticeRecord, str | None]] = []

    def create(self, notice_id: str, payload: NoticeCreate, actor: UUID) -> NoticeRecord:
        record = new_record(notice_id, payload)
        self._check_festival(record.festival_id)
        with self._lock:
            self._records[notice_id] = record
            self.events.append(("create", actor, None, record, None))
        return record

    def change(
        self, notice_id: str, action: Action, actor: UUID,
        *, patch: NoticeUpdate | None = None, reason: str | None = None,
    ) -> NoticeRecord:
        with self._lock:
            before = self._records.get(notice_id)
            if before is None:
                raise notice_not_found()
            now = self._clock()
            after = apply_change(before, action, now, patch)
            if before.festival_id != after.festival_id:
                self._check_festival(after.festival_id)

            previously_approved = before.approval_status == "approved"
            if previously_approved or action == "approve":
                scope = before.festival_id if previously_approved else after.festival_id
                changes = [(key, when) for key, when in self._changes.get(notice_id, ()) if when <= now]
                changes.append((scope, now))
                if action == "approve":
                    changes.extend(
                        (scope, when) for when in (after.effective_from, after.effective_end)
                        if when is not None and when > now
                    )
                self._changes[notice_id] = changes
            if action in ("approve", "end"):
                after = replace(after, control_version=self._version(after.festival_id, now))
            self._records[notice_id] = after
            self.events.append((action, actor, before, after, reason))
            return after

    @staticmethod
    def _check_festival(festival_id: str | None) -> None:
        if festival_id is not None and find_festival(festival_id) is None:
            raise festival_not_found()

    def _public(
        self, festival_id: str, notice_type: NoticeType | None, active_only: bool, now: datetime,
    ) -> list[NoticeRecord]:
        return [
            record for record in self._records.values()
            if record.festival_id in (None, festival_id)
            and record.approval_status == "approved"
            and (notice_type is None or record.type == notice_type)
            and (not active_only or active_at(record.effective_from, record.effective_end, now))
        ]

    def approved(self, festival_id: str, notice_type: NoticeType | None, active_only: bool) -> list[Notice]:
        with self._lock:
            return [record.public() for record in self._public(festival_id, notice_type, active_only, self._clock())]

    def _version(self, festival_id: str | None, now: datetime) -> str:
        return control_version(sum(
            key in (None, festival_id) and when <= now
            for changes in self._changes.values() for key, when in changes
        ))

    def snapshot(self, festival_id: str, now: datetime | None = None) -> ControlSnapshot:
        with self._lock:
            now = now if now is not None else self._clock()
            active = sorted(
                self._public(festival_id, None, True, now),
                key=lambda record: (record.effective_from or now, record.notice_id), reverse=True,
            )
            return ControlSnapshot(
                self._version(festival_id, now), tuple(record.title for record in active if record.type != "operation"),
            )


memory_store = MemoryNoticeStore()
