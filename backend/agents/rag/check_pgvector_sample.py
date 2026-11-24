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

from agents.rag.evaluate_sample import AS_OF, DIMENSIONS, DOCUMENTS, MODEL, QUESTIONS, embed


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
            cur.execute("""
                CREATE TEMP TABLE rag_documents_test (
                    document_id text PRIMARY KEY,
                    festival_id text NOT NULL,
                    source_url text NOT NULL,
                    approval_status text NOT NULL,
                    effective_to timestamptz
                ) ON COMMIT PRESERVE ROWS
            """)
            cur.execute(f"""
                CREATE TEMP TABLE rag_chunks_test (
                    document_id text NOT NULL,
                    content text NOT NULL,
                    embedding vector({DIMENSIONS}) NOT NULL,
                    embedding_model text NOT NULL,
                    embedding_version text NOT NULL
                ) ON COMMIT PRESERVE ROWS
            """)
            cur.execute("CREATE INDEX rag_chunks_test_hnsw ON rag_chunks_test USING hnsw (embedding vector_cosine_ops)")

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
                    "INSERT INTO rag_documents_test VALUES (%s, %s, %s, 'approved', %s)",
                    (doc["id"], doc["festival"], doc["source_url"], doc["effective_to"]),
                )
                cur.execute(
                    "INSERT INTO rag_chunks_test VALUES (%s, %s, %s::vector, %s, %s)",
                    (doc["id"], doc["text"], vector_literal(vectors[index]), MODEL, "sample-v1"),
                )

            # Duplicate a valid vector with pending status so approval filtering
            # has a positive control even though its similarity is high.
            cur.execute(
                "INSERT INTO rag_documents_test VALUES ('D4_PENDING', %s, %s, 'pending', %s)",
                (DOCUMENTS[0]["festival"], DOCUMENTS[0]["source_url"], DOCUMENTS[0]["effective_to"]),
            )
            cur.execute(
                "INSERT INTO rag_chunks_test VALUES ('D4_PENDING', %s, %s::vector, %s, %s)",
                (DOCUMENTS[0]["text"], vector_literal(vectors[0]), MODEL, "sample-v1"),
            )

            passed = 0
            query_seconds = 0.0
            for index, (question_id, festival_id, _question, expected) in enumerate(QUESTIONS):
                started = time.monotonic()
                cur.execute("""
                    SELECT d.document_id, d.festival_id,
                           ROUND((1 - (c.embedding <=> %s::vector))::numeric, 4)
                    FROM rag_chunks_test AS c
                    JOIN rag_documents_test AS d ON d.document_id = c.document_id
                    WHERE d.approval_status = 'approved'
                      AND d.festival_id = %s
                      AND (d.effective_to IS NULL OR %s::timestamptz < d.effective_to)
                      AND c.embedding_model = %s
                      AND c.embedding_version = 'sample-v1'
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT 5
                """, (
                    vector_literal(vectors[len(DOCUMENTS) + index]),
                    festival_id,
                    AS_OF,
                    MODEL,
                    vector_literal(vectors[len(DOCUMENTS) + index]),
                ))
                rows = cur.fetchall()
                query_seconds += time.monotonic() - started
                ids = [row[0] for row in rows]
                valid = (
                    (expected is None or (ids and ids[0] == expected))
                    and (question_id != "Q07" or not rows)
                    and "D4_PENDING" not in ids
                    and all(row[1] == festival_id for row in rows)
                )
                print(f"{question_id}: ranked={[(row[0], float(row[2])) for row in rows]}, filters_ok={valid}")
                passed += bool(valid)
            print(f"pgvector filters/retrieval: {passed}/{len(QUESTIONS)}; model={MODEL}; dimensions={DIMENSIONS}")
            print(f"embedding_seconds={embedding_seconds}, query_seconds={round(query_seconds, 3)}, usage={usage}")
            print("Temporary rows only; no service RAG tables were written. Answer generation was not tested.")
            return 0 if passed == len(QUESTIONS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
