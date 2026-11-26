"""Embed a question and retrieve approved festival evidence candidates."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from agents.rag.embedding import MODEL, embed_texts
from agents.rag.search import search_festival_evidence


def retrieve_festival_question(
    connection,
    *,
    festival_id: str,
    question: str,
    as_of: datetime,
    embedding_version: str,
    api_key: str,
    limit: int = 5,
) -> dict:
    """Return source-bearing candidates, never an answer or approval decision."""
    if not isinstance(festival_id, str) or not festival_id.strip():
        raise ValueError("festival_id is required")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    if len(question) > 500:
        raise ValueError("question exceeds the A06 message limit")
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    if not isinstance(embedding_version, str) or not embedding_version.strip():
        raise ValueError("embedding_version is required")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    vectors, usage = embed_texts([question], api_key)
    candidates = search_festival_evidence(
        connection,
        festival_id=festival_id,
        query_vector=vectors[0],
        as_of=as_of,
        embedding_model=MODEL,
        embedding_version=embedding_version,
        limit=limit,
    )
    for candidate in candidates:
        source = candidate.get("source_url")
        parsed = urlparse(source) if isinstance(source, str) else None
        if (candidate.get("festival_id") != festival_id
                or not candidate.get("document_id") or not candidate.get("chunk_id")
                or not isinstance(candidate.get("content"), str) or not candidate["content"].strip()
                or parsed is None or parsed.scheme != "https" or not parsed.hostname):
            raise ValueError("retrieved evidence is missing matching festival identity or source")
    return {
        "status": "candidates" if candidates else "no_evidence",
        "festival_id": festival_id,
        "as_of": as_of.isoformat(),
        "embedding_model": MODEL,
        "embedding_version": embedding_version,
        "candidates": candidates,
        "embedding_usage": usage,
    }
