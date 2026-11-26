"""AUTH_PROVIDER=mock에서 쓰는 RAG 공식 문서 검토 메모리 저장소(시험·화면 연동용)."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from uuid import UUID

from api.schemas.rag_documents import (
    RagChunkPreview, RagDocumentDetail, RagDocumentEvent, RagDocumentItem, RagDocumentPage,
    RagDocumentQuery, RagDocumentReview, RagDocumentReviewResult,
)
from api.services.notices import now_kst
from api.services.rag_documents import (
    MAX_PREVIEW_CHUNKS, PREVIEW_CHARS, already_reviewed, checksum_mismatch, document_not_found, no_chunks,
    supersede_cutoff,
)


@dataclass
class MemoryDocument:
    item: RagDocumentItem
    chunks: list[RagChunkPreview] = field(default_factory=list)
    events: list[RagDocumentEvent] = field(default_factory=list)


class MemoryRagDocumentStore:
    def __init__(self, clock: Callable[[], datetime] = now_kst) -> None:
        self._clock = clock
        self._lock = Lock()
        self._documents: dict[UUID, MemoryDocument] = {}

    def add(self, item: RagDocumentItem, chunk_texts: list[str] | None = None) -> None:
        chunks = [
            RagChunkPreview(chunk_index=index, preview=text[:PREVIEW_CHARS],
                            embedding_model="mock", embedding_version="mock")
            for index, text in enumerate(chunk_texts or [])
        ]
        with self._lock:
            self._documents[item.document_id] = MemoryDocument(
                replace_item(item, chunk_count=len(chunks)), chunks,
            )

    def list(self, query: RagDocumentQuery) -> RagDocumentPage:
        with self._lock:
            rows = [
                doc.item for doc in self._documents.values()
                if (query.approval_status is None or doc.item.approval_status == query.approval_status)
                and (query.festival_id is None or doc.item.festival_id == query.festival_id)
            ]
        rows.sort(key=lambda item: (item.created_at, str(item.document_id)), reverse=True)
        start = (query.page - 1) * query.page_size
        return RagDocumentPage(
            items=rows[start:start + query.page_size], page=query.page, page_size=query.page_size, total=len(rows),
        )

    def get(self, document_id: UUID) -> RagDocumentDetail:
        with self._lock:
            doc = self._documents.get(document_id)
            if doc is None:
                raise document_not_found()
            return RagDocumentDetail(
                **doc.item.model_dump(), chunks=doc.chunks[:MAX_PREVIEW_CHUNKS], events=list(doc.events),
            )

    def review(self, document_id: UUID, payload: RagDocumentReview, actor: UUID) -> RagDocumentReviewResult:
        with self._lock:
            doc = self._documents.get(document_id)
            if doc is None:
                raise document_not_found()
            item = doc.item
            if item.approval_status != "pending":
                raise already_reviewed()
            if item.checksum != payload.checksum:
                raise checksum_mismatch()
            now = self._clock()
            superseded: list[UUID] = []
            if payload.decision == "reject":
                doc.item = replace_item(item, approval_status="rejected")
                doc.events.append(RagDocumentEvent(action="reject", actor=actor, reason=payload.reason, created_at=now))
            else:
                if item.chunk_count == 0:
                    raise no_chunks()
                cutoff = supersede_cutoff(item.effective_from, now)
                for other in self._documents.values():
                    old = other.item
                    if (old.document_id != item.document_id and old.approval_status == "approved"
                            and old.festival_id == item.festival_id and old.source_url == item.source_url
                            and (old.effective_to is None or old.effective_to > cutoff)):
                        other.item = replace_item(old, effective_to=cutoff)
                        other.events.append(RagDocumentEvent(
                            action="supersede", actor=actor, reason=f"개정본 {item.document_id} 승인", created_at=now,
                        ))
                        superseded.append(old.document_id)
                doc.item = replace_item(item, approval_status="approved", approved_by=actor, approved_at=now)
                doc.events.append(RagDocumentEvent(action="approve", actor=actor, reason=payload.reason, created_at=now))
            result = doc.item
        return RagDocumentReviewResult(
            document_id=result.document_id, approval_status=result.approval_status, approved_by=result.approved_by,
            approved_at=result.approved_at, effective_from=result.effective_from, effective_to=result.effective_to,
            superseded_document_ids=sorted(superseded, key=str),
        )


def replace_item(item: RagDocumentItem, **changes: object) -> RagDocumentItem:
    return item.model_copy(update=changes)


memory_store = MemoryRagDocumentStore()
