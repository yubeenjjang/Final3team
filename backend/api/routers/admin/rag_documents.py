"""A83~A85 운영자 RAG 공식 문서 목록·상세·승인/반려 (W27 계약 2·3절)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from api.auth.tokens import uses_auth_db
from api.deps import CurrentUser, require_role
from api.mocks import rag_documents as mock_rag_documents
from api.repositories.rag_documents import postgres_store
from api.schemas.rag_documents import (
    RagDocumentDetail, RagDocumentPage, RagDocumentQuery, RagDocumentReview, RagDocumentReviewResult,
)
from api.services.rag_documents import RagDocumentStore

router = APIRouter(prefix="/admin/rag-documents")
Operator = Annotated[CurrentUser, Depends(require_role("operator", "admin"))]


def _store() -> RagDocumentStore:
    return postgres_store if uses_auth_db() else mock_rag_documents.memory_store


@router.get("")
def list_rag_documents(query: Annotated[RagDocumentQuery, Query()], operator: Operator) -> RagDocumentPage:
    return _store().list(query)


@router.get("/{document_id}")
def get_rag_document(document_id: UUID, operator: Operator) -> RagDocumentDetail:
    return _store().get(document_id)


@router.post("/{document_id}/review")
def review_rag_document(
    document_id: UUID, payload: RagDocumentReview, operator: Operator,
) -> RagDocumentReviewResult:
    return _store().review(document_id, payload, operator.claims.user_id)
