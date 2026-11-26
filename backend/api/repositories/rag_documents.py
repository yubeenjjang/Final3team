"""001 rag_documents·rag_chunks와 029 rag_document_events의 PostgreSQL 저장소(A83~A85)."""

import json
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, TimeoutError as DBPoolTimeout
from sqlalchemy.orm import Session

from api.errors import ApiError
from api.schemas.rag_documents import (
    RagChunkPreview, RagDocumentDetail, RagDocumentEvent, RagDocumentItem, RagDocumentPage,
    RagDocumentQuery, RagDocumentReview, RagDocumentReviewResult,
)
from api.services.rag_documents import (
    MAX_PREVIEW_CHUNKS, PREVIEW_CHARS, already_reviewed, checksum_mismatch, document_not_found,
    festival_not_public, no_chunks, store_unavailable, supersede_cutoff,
)
from shared.db.session import service_db_session

_ITEM = """
    d.document_id, d.festival_id, d.title, d.category, d.authored_by, d.source_url, d.publisher,
    d.published_at, d.effective_from, d.effective_to, d.collected_at, d.approval_status,
    d.approved_by, d.approved_at, d.checksum, d.created_at,
    (SELECT count(*) FROM public.rag_chunks c WHERE c.document_id = d.document_id) AS chunk_count
"""
_FILTER = """
    WHERE (CAST(:status AS text) IS NULL OR d.approval_status = :status)
      AND (CAST(:festival_id AS text) IS NULL OR d.festival_id = :festival_id)
"""


class PostgresRagDocumentStore:
    def __init__(self, session: Callable[[], AbstractContextManager[Session]] = service_db_session) -> None:
        self._session = session

    @contextmanager
    def _transaction(self) -> Iterator[Session]:
        try:
            with self._session() as session:
                yield session
        except (ApiError, DBPoolTimeout):
            raise
        except (SQLAlchemyError, RuntimeError, ValueError):
            raise store_unavailable() from None

    def list(self, query: RagDocumentQuery) -> RagDocumentPage:
        params = {
            "status": query.approval_status, "festival_id": query.festival_id,
            "limit": query.page_size, "offset": (query.page - 1) * query.page_size,
        }
        with self._transaction() as session:
            total = session.execute(text(f"SELECT count(*) FROM public.rag_documents d {_FILTER}"), params).scalar_one()
            rows = session.execute(text(f"""
                SELECT {_ITEM} FROM public.rag_documents d {_FILTER}
                ORDER BY d.created_at DESC, d.document_id DESC LIMIT :limit OFFSET :offset
            """), params).mappings().all()
        return RagDocumentPage(
            items=[RagDocumentItem(**row) for row in rows], page=query.page, page_size=query.page_size, total=total,
        )

    def get(self, document_id: UUID) -> RagDocumentDetail:
        with self._transaction() as session:
            row = session.execute(text(f"SELECT {_ITEM} FROM public.rag_documents d WHERE d.document_id = :id"),
                                  {"id": document_id}).mappings().one_or_none()
            if row is None:
                raise document_not_found()
            # 임베딩 벡터는 내보내지 않는다.
            chunks = session.execute(text("""
                SELECT chunk_index, left(content, :chars) AS preview, embedding_model, embedding_version
                FROM public.rag_chunks WHERE document_id = :id ORDER BY chunk_index LIMIT :limit
            """), {"id": document_id, "chars": PREVIEW_CHARS, "limit": MAX_PREVIEW_CHUNKS}).mappings().all()
            events = session.execute(text("""
                SELECT action, actor, reason, created_at FROM public.rag_document_events
                WHERE document_id = :id ORDER BY created_at, event_id
            """), {"id": document_id}).mappings().all()
        return RagDocumentDetail(
            **row, chunks=[RagChunkPreview(**chunk) for chunk in chunks],
            events=[RagDocumentEvent(**event) for event in events],
        )

    def review(self, document_id: UUID, payload: RagDocumentReview, actor: UUID) -> RagDocumentReviewResult:
        with self._transaction() as session:
            row = session.execute(text("""
                SELECT document_id, festival_id, source_url, approval_status, checksum,
                       effective_from, effective_to, approved_by, approved_at
                FROM public.rag_documents WHERE document_id = :id FOR UPDATE
            """), {"id": document_id}).mappings().one_or_none()
            if row is None:
                raise document_not_found()
            if row["approval_status"] != "pending":
                raise already_reviewed()
            if row["checksum"] != payload.checksum:
                raise checksum_mismatch()
            now: datetime = session.execute(text("SELECT clock_timestamp()")).scalar_one()
            superseded: list[UUID] = []
            if payload.decision == "reject":
                session.execute(text("""
                    UPDATE public.rag_documents SET approval_status = 'rejected' WHERE document_id = :id
                """), {"id": document_id})
                self._event(session, document_id, "reject", actor, row["checksum"], payload.reason,
                            {"approval_status": "pending"}, {"approval_status": "rejected"})
                status, approved_by, approved_at, effective_to = "rejected", None, None, row["effective_to"]
            else:
                self._check_approvable(session, document_id, row["festival_id"])
                # 같은 축제·원문 URL의 개정본 승인을 직렬화해 두 승인본의 효력이 겹치지 않게 한다.
                session.execute(text("""
                    SELECT pg_advisory_xact_lock(hashtextextended(
                        'noldaga.rag:' || coalesce(CAST(:festival_id AS text), '') || '|' || :source_url, 0))
                """), {"festival_id": row["festival_id"], "source_url": row["source_url"]})
                cutoff = supersede_cutoff(row["effective_from"], now)
                closed = session.execute(text("""
                    UPDATE public.rag_documents old
                    SET effective_to = :cutoff
                    FROM (SELECT document_id, effective_to FROM public.rag_documents
                          WHERE approval_status = 'approved' AND document_id <> :id
                            AND festival_id IS NOT DISTINCT FROM CAST(:festival_id AS text)
                            AND source_url = :source_url
                            AND (effective_to IS NULL OR effective_to > :cutoff)
                          FOR UPDATE) prev
                    WHERE old.document_id = prev.document_id
                    RETURNING old.document_id, prev.effective_to AS before_effective_to
                """), {"id": document_id, "festival_id": row["festival_id"], "source_url": row["source_url"],
                       "cutoff": cutoff}).mappings().all()
                for old in closed:
                    superseded.append(old["document_id"])
                    self._event(session, old["document_id"], "supersede", actor, None, f"개정본 {document_id} 승인",
                                {"effective_to": old["before_effective_to"]}, {"effective_to": cutoff})
                session.execute(text("""
                    UPDATE public.rag_documents
                    SET approval_status = 'approved', approved_by = :actor, approved_at = :now
                    WHERE document_id = :id
                """), {"id": document_id, "actor": actor, "now": now})
                self._event(session, document_id, "approve", actor, row["checksum"], payload.reason,
                            {"approval_status": "pending"},
                            {"approval_status": "approved", "approved_by": str(actor), "approved_at": now})
                status, approved_by, approved_at, effective_to = "approved", actor, now, row["effective_to"]
        return RagDocumentReviewResult(
            document_id=document_id, approval_status=status, approved_by=approved_by, approved_at=approved_at,
            effective_from=row["effective_from"], effective_to=effective_to,
            superseded_document_ids=sorted(superseded, key=str),
        )

    @staticmethod
    def _check_approvable(session: Session, document_id: UUID, festival_id: str | None) -> None:
        if session.execute(text("SELECT EXISTS (SELECT 1 FROM public.rag_chunks WHERE document_id = :id)"),
                           {"id": document_id}).scalar_one() is not True:
            raise no_chunks()
        if festival_id is not None and session.execute(text("""
            SELECT festival_id FROM public.festivals
            WHERE festival_id = :festival_id AND published_at IS NOT NULL FOR KEY SHARE
        """), {"festival_id": festival_id}).scalar_one_or_none() is None:
            raise festival_not_public()

    @staticmethod
    def _event(
        session: Session, document_id: UUID, action: str, actor: UUID, checksum: str | None, reason: str | None,
        before: dict, after: dict,
    ) -> None:
        session.execute(text("""
            INSERT INTO public.rag_document_events
              (document_id, action, actor, checksum, before_value, after_value, reason)
            VALUES (:document_id, :action, :actor, :checksum, CAST(:before AS jsonb), CAST(:after AS jsonb), :reason)
        """), {
            "document_id": document_id, "action": action, "actor": actor, "checksum": checksum, "reason": reason,
            "before": json.dumps(before, default=_json_default, ensure_ascii=False),
            "after": json.dumps(after, default=_json_default, ensure_ascii=False),
        })


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


postgres_store = PostgresRagDocumentStore()
