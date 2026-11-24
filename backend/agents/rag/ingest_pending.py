"""Prepare and store a manually reviewed festival source as pending RAG data.

This module never approves a document or fetches an arbitrary URL. A separate
administrator review must set approval_status before search can return it.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import uuid
from datetime import datetime
from urllib.parse import urlparse


CATEGORIES = {"operation_notice", "safety", "transport_guide", "faq", "tip"}


def chunk_sections(title: str, sections: list[tuple[str, str]], *, size: int = 500, overlap: int = 50) -> list[str]:
    """Keep short titled items intact; split only items longer than size."""
    if not title.strip() or not sections:
        raise ValueError("title and at least one section are required")
    if size < 100 or not 0 <= overlap < size:
        raise ValueError("invalid chunk size or overlap")
    chunks: list[str] = []
    for heading, body in sections:
        heading, body = heading.strip(), body.strip()
        if not heading or not body:
            raise ValueError("each section needs a heading and content")
        prefix = f"{title.strip()} / {heading}: "
        if len(prefix) >= size:
            raise ValueError("title and section heading are too long")
        capacity = size - len(prefix)
        if len(body) <= capacity:
            chunks.append(prefix + body)
            continue
        if overlap >= capacity:
            raise ValueError("overlap leaves no room for new content")
        step = capacity - overlap
        for start in range(0, len(body), step):
            chunks.append(prefix + body[start:start + capacity])
            if start + capacity >= len(body):
                break
    return chunks


def store_pending_document(
    connection,
    *,
    festival_id: str,
    title: str,
    category: str,
    source_url: str,
    publisher: str | None,
    published_at: datetime | None,
    effective_from: datetime | None,
    effective_to: datetime | None,
    collected_at: datetime,
    chunks: list[str],
    embeddings: list[list[float]],
    embedding_model: str,
    embedding_version: str,
) -> tuple[str, bool]:
    """Insert pending metadata and vectors atomically; return (ID, inserted)."""
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("source_url must be a public HTTPS URL without credentials")
    if parsed.hostname == "localhost":
        raise ValueError("source_url must not point to localhost")
    try:
        source_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        source_ip = None
    if source_ip is not None and not source_ip.is_global:
        raise ValueError("source_url must not point to a private address")
    if not festival_id or not title.strip() or category not in CATEGORIES:
        raise ValueError("festival ID, title, and supported category are required")
    if not chunks or len(chunks) != len(embeddings) or any(not part.strip() for part in chunks):
        raise ValueError("each chunk requires one embedding")
    if not embedding_model or not embedding_version:
        raise ValueError("embedding model and version are required")
    for timestamp in (published_at, effective_from, effective_to, collected_at):
        if timestamp is not None and (timestamp.tzinfo is None or timestamp.utcoffset() is None):
            raise ValueError("all supplied timestamps must include a timezone")
    if effective_from and effective_to and effective_from >= effective_to:
        raise ValueError("effective_to must be later than effective_from")
    if any(len(vector) != 1024 or not all(math.isfinite(value) for value in vector) for vector in embeddings):
        raise ValueError("each embedding must contain 1024 finite values")

    checksum_source = {
        "title": title.strip(),
        "category": category,
        "chunks": chunks,
        "published_at": published_at.isoformat() if published_at else None,
        "effective_from": effective_from.isoformat() if effective_from else None,
        "effective_to": effective_to.isoformat() if effective_to else None,
    }
    checksum = hashlib.sha256(json.dumps(checksum_source, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    document_id = str(uuid.uuid4())
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute("SELECT 1 FROM festivals WHERE festival_id = %s", (festival_id,))
            if cur.fetchone() is None:
                raise ValueError("festival_id is not present in the catalog")
            cur.execute("""
                INSERT INTO rag_documents (
                    document_id, festival_id, title, category, source_url, publisher,
                    published_at, effective_from, effective_to, collected_at,
                    approval_status, checksum
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s
                ) ON CONFLICT (source_url, checksum) DO NOTHING
                RETURNING document_id
            """, (
                document_id, festival_id, title.strip(), category, source_url, publisher,
                published_at, effective_from, effective_to, collected_at, checksum,
            ))
            inserted = cur.fetchone()
            if inserted is None:
                cur.execute(
                    "SELECT document_id, festival_id FROM rag_documents WHERE source_url = %s AND checksum = %s",
                    (source_url, checksum),
                )
                existing = cur.fetchone()
                if existing is None:
                    raise RuntimeError("duplicate document could not be found")
                if existing[1] != festival_id:
                    raise ValueError("existing source revision belongs to another festival")
                return str(existing[0]), False
            for index, (content, vector) in enumerate(zip(chunks, embeddings, strict=True)):
                cur.execute("""
                    INSERT INTO rag_chunks (
                        chunk_id, document_id, chunk_index, content, embedding,
                        embedding_model, embedding_version
                    ) VALUES (%s, %s, %s, %s, %s::vector, %s, %s)
                """, (
                    str(uuid.uuid4()), document_id, index, content,
                    json.dumps(vector, separators=(",", ":")), embedding_model, embedding_version,
                ))
    return document_id, True
