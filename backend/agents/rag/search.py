"""Search approved, currently effective festival documents with pgvector.

The caller supplies a vector from the configured embedding model. This module
only retrieves evidence; answer generation and source acceptance are separate.
"""

from __future__ import annotations

import math
from datetime import datetime


SEARCH_SQL = """
SELECT c.chunk_id, c.document_id, d.festival_id, d.source_url,
       d.publisher, d.published_at, d.effective_from, d.effective_to,
       c.content, c.embedding <=> %s::vector AS cosine_distance
FROM rag_chunks AS c
JOIN rag_documents AS d ON d.document_id = c.document_id
WHERE d.approval_status = 'approved'
  AND d.festival_id = %s
  AND (d.effective_from IS NULL OR d.effective_from <= %s::timestamptz)
  AND (d.effective_to IS NULL OR %s::timestamptz < d.effective_to)
  AND c.embedding_model = %s
  AND c.embedding_version = %s
ORDER BY c.embedding <=> %s::vector
LIMIT %s
"""


def search_festival_evidence(
    connection,
    *,
    festival_id: str,
    query_vector: list[float],
    as_of: datetime,
    embedding_model: str,
    embedding_version: str,
    limit: int = 5,
) -> list[dict]:
    """Return source-bearing chunks for one festival; never include pending rows."""
    if not festival_id or not isinstance(festival_id, str):
        raise ValueError("festival_id is required")
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    if len(query_vector) != 1024 or not all(math.isfinite(value) for value in query_vector):
        raise ValueError("query_vector must contain 1024 finite values")
    if not embedding_model or not embedding_version:
        raise ValueError("embedding model and version are required")
    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    vector = "[" + ",".join(str(value) for value in query_vector) + "]"
    with connection.cursor() as cur:
        cur.execute(
            SEARCH_SQL,
            (vector, festival_id, as_of, as_of, embedding_model, embedding_version, vector, limit),
        )
        rows = cur.fetchall()
    return [
        {
            "chunk_id": str(row[0]),
            "document_id": str(row[1]),
            "festival_id": row[2],
            "source_url": row[3],
            "publisher": row[4],
            "published_at": row[5],
            "effective_from": row[6],
            "effective_to": row[7],
            "content": row[8],
            "cosine_distance": float(row[9]),
        }
        for row in rows
    ]
