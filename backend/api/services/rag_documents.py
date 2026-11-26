"""RAG 공식 문서 승인 규칙(W27 계약 2·3절)과 저장소 인터페이스.

- 승인·반려는 pending 문서만, 운영자가 검토한 checksum이 현재 값과 같을 때만 처리한다.
- 승인자·승인 시각은 요청 본문이 아니라 서버가 확인한 계정과 서버 시각으로 기록한다.
- 같은 축제·같은 원문 URL의 개정본을 승인하면 기존 승인본의 효력 끝을 새 문서 효력 시작으로 닫아
  두 승인본이 같은 시각에 검색되지 않게 한다.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from api.errors import ApiError
from api.schemas.rag_documents import (
    RagDocumentDetail, RagDocumentPage, RagDocumentQuery, RagDocumentReview, RagDocumentReviewResult,
)

PREVIEW_CHARS = 200
MAX_PREVIEW_CHUNKS = 50


def document_not_found() -> ApiError:
    return ApiError(404, "RAG_DOCUMENT_NOT_FOUND", "문서를 찾을 수 없어요.")


def already_reviewed() -> ApiError:
    return ApiError(409, "RAG_DOCUMENT_ALREADY_REVIEWED", "이미 승인 또는 반려된 문서예요.")


def checksum_mismatch() -> ApiError:
    return ApiError(409, "RAG_DOCUMENT_CHANGED", "검토한 뒤 문서 내용이 바뀌었어요. 다시 확인해 주세요.")


def no_chunks() -> ApiError:
    return ApiError(409, "RAG_DOCUMENT_EMPTY", "검색에 쓸 본문 조각이 없는 문서는 승인할 수 없어요.")


def festival_not_public() -> ApiError:
    return ApiError(409, "RAG_FESTIVAL_NOT_PUBLIC", "공개된 축제의 문서만 승인할 수 있어요.")


def store_unavailable() -> ApiError:
    return ApiError(503, "RAG_DOCUMENT_STORE_UNAVAILABLE", "문서를 처리할 수 없어요. 잠시 뒤 다시 시도해 주세요.", True)


def supersede_cutoff(effective_from: datetime | None, now: datetime) -> datetime:
    """기존 승인본을 닫는 시각: 새 문서 효력 시작, 없으면 승인 시각."""
    return effective_from or now


class RagDocumentStore(Protocol):
    def list(self, query: RagDocumentQuery) -> RagDocumentPage: ...

    def get(self, document_id: UUID) -> RagDocumentDetail: ...

    def review(self, document_id: UUID, payload: RagDocumentReview, actor: UUID) -> RagDocumentReviewResult: ...
