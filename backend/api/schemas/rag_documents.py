"""A83~A85 운영자 RAG 공식 문서 검토 요청·응답."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from api.schemas.festivals import FESTIVAL_ID_PATTERN
from api.schemas.notices import ApprovalStatus, Reason

RagCategory = Literal["operation_notice", "safety", "transport_guide", "faq", "tip", "app_guide"]
RagAuthor = Literal["source", "team", "llm_draft"]
Checksum = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
FestivalFilter = Annotated[str, StringConstraints(pattern=FESTIVAL_ID_PATTERN)]


class RagDocumentQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_status: ApprovalStatus | None = None
    festival_id: FestivalFilter | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RagDocumentItem(BaseModel):
    document_id: UUID
    festival_id: str | None
    title: str
    category: RagCategory
    authored_by: RagAuthor
    source_url: str
    publisher: str | None
    published_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    collected_at: datetime
    approval_status: ApprovalStatus
    approved_by: UUID | None
    approved_at: datetime | None
    checksum: str
    chunk_count: int
    created_at: datetime


class RagDocumentPage(BaseModel):
    items: list[RagDocumentItem]
    page: int
    page_size: int
    total: int


class RagChunkPreview(BaseModel):
    chunk_index: int
    preview: str
    embedding_model: str
    embedding_version: str


class RagDocumentEvent(BaseModel):
    action: Literal["approve", "reject", "supersede"]
    actor: UUID
    reason: str | None
    created_at: datetime


class RagDocumentDetail(RagDocumentItem):
    chunks: list[RagChunkPreview]
    events: list[RagDocumentEvent]


class RagDocumentReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    checksum: Checksum
    reason: Reason | None = None

    @model_validator(mode="after")
    def validate_rejection(self) -> "RagDocumentReview":
        if self.decision == "reject" and self.reason is None:
            raise ValueError("반려 사유가 필요합니다.")
        return self


class RagDocumentReviewResult(BaseModel):
    document_id: UUID
    approval_status: ApprovalStatus
    approved_by: UUID | None
    approved_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    superseded_document_ids: list[UUID]
