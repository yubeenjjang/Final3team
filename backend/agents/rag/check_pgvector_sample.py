"""Exercise the RAG filters and cosine search in a disposable pgvector DB.

The database must be named rag_scratch. All document/chunk rows live in
temporary tables and disappear when the connection closes. This is not an
ingestion or approval path for the service database.
"""

from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from datetime import datetime

from agents.rag.evaluate_sample import AS_OF, DIMENSIONS, DOCUMENTS, MODEL, QUESTIONS, embed
from agents.rag.ingest_pending import store_pending_document
from agents.rag.search import search_festival_evidence


def vector_literal(values: list[float]) -> str:
    return json.dumps(values, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55432)
    parser.add_argument("--user", default="postgres")
    args = parser.parse_args()

    try:
        import psycopg
    except ImportError:
        print("Install psycopg[binary] in the test environment first.", file=sys.stderr)
        return 2

    db_password = getpass.getpass("Disposable rag_scratch DB password (hidden): ")
    try:
        connection = psycopg.connect(
            host=args.host,
            port=args.port,
            dbname="rag_scratch",
            user=args.user,
            password=db_password,
            connect_timeout=5,
        )
    except psycopg.Error as exc:
        print(f"Could not connect to rag_scratch: {exc}", file=sys.stderr)
        return 2
    finally:
        db_password = ""

    with connection:
        with connection.cursor() as cur:
            cur.execute("SELECT current_database()")
            if cur.fetchone()[0] != "rag_scratch":
                print("Refusing to use a database other than rag_scratch.", file=sys.stderr)
                return 2
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("CREATE TEMP TABLE festivals (festival_id text PRIMARY KEY) ON COMMIT PRESERVE ROWS")
            cur.execute("INSERT INTO festivals VALUES (%s)", (DOCUMENTS[0]["festival"],))
            cur.execute("""
                CREATE TEMP TABLE rag_documents (
                    document_id text PRIMARY KEY,
                    festival_id text NOT NULL,
                    title text NOT NULL DEFAULT 'sample',
                    category text NOT NULL DEFAULT 'faq',
                    source_url text NOT NULL,
                    publisher text,
                    published_at timestamptz,
                    effective_from timestamptz,
                    effective_to timestamptz,
                    collected_at timestamptz NOT NULL DEFAULT now(),
                    approval_status text NOT NULL,
                    checksum text NOT NULL DEFAULT 'sample',
                    UNIQUE (source_url, checksum)
                ) ON COMMIT PRESERVE ROWS
            """)
            cur.execute(f"""
                CREATE TEMP TABLE rag_chunks (
                    chunk_id text NOT NULL,
                    document_id text NOT NULL,
                    chunk_index int NOT NULL,
                    content text NOT NULL,
                    embedding vector({DIMENSIONS}) NOT NULL,
                    embedding_model text NOT NULL,
                    embedding_version text NOT NULL
                ) ON COMMIT PRESERVE ROWS
            """)
            cur.execute("CREATE INDEX rag_chunks_scratch_hnsw ON rag_chunks USING hnsw (embedding vector_cosine_ops)")

            api_key = getpass.getpass("OpenAI API key (hidden; not saved): ").strip()
            if not api_key:
                print("No API key entered; stopped before the API call.", file=sys.stderr)
                return 2
            started = time.monotonic()
            try:
                texts = [doc["text"] for doc in DOCUMENTS] + [question for _, _, question, _ in QUESTIONS]
                vectors, usage = embed(texts, api_key)
            finally:
                api_key = ""
            embedding_seconds = round(time.monotonic() - started, 3)

            for index, doc in enumerate(DOCUMENTS):
                cur.execute(
                    "INSERT INTO rag_documents (document_id, festival_id, source_url, approval_status, effective_to) VALUES (%s, %s, %s, 'approved', %s)",
                    (doc["id"], doc["festival"], doc["source_url"], doc["effective_to"]),
                )
                cur.execute(
                    "INSERT INTO rag_chunks VALUES (%s, %s, 0, %s, %s::vector, %s, %s)",
                    (f"{doc['id']}-C1", doc["id"], doc["text"], vector_literal(vectors[index]), MODEL, "sample-v1"),
                )

            # The pending ingestion path must be idempotent and invisible to search.
            pending_args = dict(
                festival_id=DOCUMENTS[0]["festival"],
                title="서울빛초롱축제 시험 문서",
                category="faq",
                source_url=DOCUMENTS[0]["source_url"],
                publisher="서울특별시",
                published_at=None,
                effective_from=None,
                effective_to=datetime.fromisoformat(DOCUMENTS[0]["effective_to"]),
                collected_at=AS_OF,
                chunks=[DOCUMENTS[0]["text"]],
                embeddings=[vectors[0]],
                embedding_model=MODEL,
                embedding_version="sample-v1",
            )
            pending_id, inserted = store_pending_document(connection, **pending_args)
            duplicate_id, duplicate_inserted = store_pending_document(connection, **pending_args)
            if not inserted or duplicate_inserted or duplicate_id != pending_id:
                raise RuntimeError("Pending document insertion was not idempotent")
            print("pending_ingestion: first_insert=True, duplicate_insert=False")

            passed = 0
            query_seconds = 0.0
            for index, (question_id, festival_id, _question, expected) in enumerate(QUESTIONS):
                started = time.monotonic()
                rows = search_festival_evidence(
                    connection,
                    festival_id=festival_id,
                    query_vector=vectors[len(DOCUMENTS) + index],
                    as_of=AS_OF,
                    embedding_model=MODEL,
                    embedding_version="sample-v1",
                )
                query_seconds += time.monotonic() - started
                ids = [row["document_id"] for row in rows]
                valid = (
                    (expected is None or (ids and ids[0] == expected))
                    and (question_id != "Q07" or not rows)
                    and pending_id not in ids
                    and all(row["festival_id"] == festival_id for row in rows)
                )
                print(f"{question_id}: ranked={[(row['document_id'], round(1 - row['cosine_distance'], 4)) for row in rows]}, filters_ok={valid}")
                passed += bool(valid)
            print(f"pgvector filters/retrieval: {passed}/{len(QUESTIONS)}; model={MODEL}; dimensions={DIMENSIONS}")
            print(f"embedding_seconds={embedding_seconds}, query_seconds={round(query_seconds, 3)}, usage={usage}")
            print("Temporary rows only; no service RAG tables were written. Answer generation was not tested.")
            return 0 if passed == len(QUESTIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
