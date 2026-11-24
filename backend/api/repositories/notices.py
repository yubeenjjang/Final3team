"""006 공지 이력과 022 축제별 통제 버전의 PostgreSQL 저장소."""

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import asdict, replace
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as DBPoolTimeout
from sqlalchemy.orm import Session

from api.errors import ApiError
from api.schemas.notices import NoticeCreate, NoticeUpdate
from api.services.notices import (
    SOURCE_ID, Action, ControlSnapshot, NoticeRecord, apply_change, control_version,
    festival_not_found, new_record, notice_not_found,
)
from shared.db.session import service_db_session

_COLUMNS = """
    notice_id, festival_id, type, title, content, effective_from, effective_to, source_url,
    approval_status, published_at, ended_at, control_version
"""
_REVISION = """
    SELECT count(*) FROM public.notice_control_changes
    WHERE (festival_id IS NULL OR festival_id = :festival_id) AND effective_at <= observation.observed_at
"""


class PostgresNoticeStore:
    def __init__(
        self, session: Callable[[], AbstractContextManager[Session]] = service_db_session,
    ) -> None:
        self._session = session

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            with self._session() as session:
                yield session
        except DBPoolTimeout:
            raise
        except (SQLAlchemyError, RuntimeError, ValueError):
            raise ApiError(503, "NOTICE_STORE_UNAVAILABLE", "공지를 처리할 수 없어요. 잠시 뒤 다시 시도해 주세요.", True) from None

    def create(self, notice_id: str, payload: NoticeCreate, actor: UUID) -> NoticeRecord:
        record = new_record(notice_id, payload)
        with self._transaction() as session:
            self._check_festival(session, record.festival_id)
            session.execute(text("""
                INSERT INTO public.official_notices (
                    notice_id, festival_id, type, title, content, effective_from, effective_to,
                    source_url, source_id
                ) VALUES (
                    :notice_id, :festival_id, :type, :title, :content, :effective_from, :effective_to,
                    :source_url, :source_id
                )
            """), {**asdict(record), "source_id": SOURCE_ID})
            self._audit(session, "create", actor, None, record, None)
        return record

    def change(
        self, notice_id: str, action: Action, actor: UUID,
        *, patch: NoticeUpdate | None = None, reason: str | None = None,
    ) -> NoticeRecord:
        with self._transaction() as session:
            row = session.execute(text(f"""
                SELECT {_COLUMNS} FROM public.official_notices
                WHERE notice_id = :notice_id FOR UPDATE
            """), {"notice_id": notice_id}).mappings().one_or_none()
            if row is None:
                raise notice_not_found()
            before = NoticeRecord(**row)
            now = session.execute(text("SELECT clock_timestamp()")).scalar_one()
            after = apply_change(before, action, now, patch)
            if before.festival_id != after.festival_id:
                self._check_festival(session, after.festival_id)
            session.execute(text("""
                UPDATE public.official_notices
                SET festival_id = :festival_id, type = :type, title = :title, content = :content,
                    effective_from = :effective_from, effective_to = :effective_to, source_url = :source_url,
                    approval_status = :approval_status, published_at = :published_at, ended_at = :ended_at,
                    control_version = :control_version
                WHERE notice_id = :notice_id
            """), asdict(after))

            if action in ("approve", "end"):
                revision = session.execute(text(f"""
                    SELECT ({_REVISION}) FROM (SELECT clock_timestamp() AS observed_at) observation
                """), {"festival_id": after.festival_id}).scalar_one()
                after = replace(after, control_version=control_version(revision))
                session.execute(text("""
                    UPDATE public.official_notices SET control_version = :version WHERE notice_id = :notice_id
                """), {"version": after.control_version, "notice_id": notice_id})

            self._audit(session, action, actor, before, after, reason)
        return after

    @staticmethod
    def _check_festival(session: Session, festival_id: str | None) -> None:
        if festival_id is not None and session.execute(text("""
            SELECT festival_id FROM public.festivals WHERE festival_id = :festival_id FOR KEY SHARE
        """), {"festival_id": festival_id}).scalar_one_or_none() is None:
            raise festival_not_found()

    @staticmethod
    def _audit(
        session: Session, action: Action, actor: UUID, before: NoticeRecord | None,
        after: NoticeRecord, reason: str | None,
    ) -> None:
        session.execute(text("""
            INSERT INTO public.notice_events (notice_id, action, actor, before_value, after_value, reason)
            VALUES (:notice_id, :action, :actor, CAST(:before AS jsonb), CAST(:after AS jsonb), :reason)
        """), {
            "notice_id": after.notice_id, "action": action, "actor": actor, "reason": reason,
            "before": json.dumps(asdict(before), default=datetime.isoformat, ensure_ascii=False) if before else None,
            "after": json.dumps(asdict(after), default=datetime.isoformat, ensure_ascii=False),
        })

    def snapshot(self, festival_id: str, now: datetime | None = None) -> ControlSnapshot:
        with self._transaction() as session:
            revision, titles = session.execute(text(f"""
                WITH observation AS (SELECT coalesce(CAST(:now AS timestamptz), statement_timestamp()) AS observed_at)
                SELECT ({_REVISION}), ARRAY(
                    SELECT title FROM public.official_notices n
                    WHERE n.approval_status = 'approved' AND n.type <> 'operation'
                      AND (n.festival_id IS NULL OR n.festival_id = :festival_id)
                      AND (n.effective_from IS NULL OR n.effective_from <= observation.observed_at)
                      AND (n.effective_to IS NULL OR n.effective_to > observation.observed_at)
                      AND (n.ended_at IS NULL OR n.ended_at > observation.observed_at)
                      AND EXISTS (
                          SELECT 1 FROM public.festivals f
                          WHERE f.festival_id = :festival_id AND f.category = 'festival'
                            AND f.source_class_level2 = 'EV01' AND f.review_status = 'approved'
                            AND f.published_at IS NOT NULL
                      )
                    ORDER BY n.effective_from DESC NULLS LAST, n.notice_id LIMIT 3
                ) FROM observation
            """), {"festival_id": festival_id, "now": now}).one()
            return ControlSnapshot(control_version(revision), tuple(titles))


postgres_store = PostgresNoticeStore()
