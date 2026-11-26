"""Keep mismatched or source-less RAG rows out of the answer path."""

import unittest
import io
import json
from datetime import datetime
from unittest.mock import patch

from agents.rag.embedding import embed_texts
from agents.rag.retrieve_question import retrieve_festival_question


AS_OF = datetime.fromisoformat("2026-11-26T10:00:00+09:00")
FESTIVAL_ID = "fst_000001"
VECTOR = [0.0] * 1024
ROW = {
    "chunk_id": "chunk-1",
    "document_id": "document-1",
    "festival_id": FESTIVAL_ID,
    "source_url": "https://festival.example.org/notice",
    "content": "축제 공식 안내",
}


class RagQuestionRetrievalTests(unittest.TestCase):
    def retrieve(self, rows):
        with (patch("agents.rag.retrieve_question.embed_texts", return_value=([VECTOR], {"total_tokens": 4})) as embed,
              patch("agents.rag.retrieve_question.search_festival_evidence", return_value=rows) as search):
            result = retrieve_festival_question(
                object(), festival_id=FESTIVAL_ID, question="언제 시작하나요?", as_of=AS_OF,
                embedding_version="official-v1", api_key="test-key",
            )
            embed.assert_called_once_with(["언제 시작하나요?"], "test-key")
            self.assertEqual(search.call_args.kwargs["festival_id"], FESTIVAL_ID)
            self.assertEqual(search.call_args.kwargs["embedding_version"], "official-v1")
            return result

    def test_approved_search_rows_become_candidates_with_source(self):
        result = self.retrieve([ROW])
        self.assertEqual(result["status"], "candidates")
        self.assertEqual(result["candidates"][0]["source_url"], ROW["source_url"])
        self.assertEqual(result["embedding_usage"], {"total_tokens": 4})

    def test_no_rows_cannot_be_treated_as_answer_evidence(self):
        result = self.retrieve([])
        self.assertEqual(result["status"], "no_evidence")
        self.assertEqual(result["candidates"], [])

    def test_mismatched_festival_or_missing_source_fails_closed(self):
        for row in ({**ROW, "festival_id": "fst_other"}, {**ROW, "source_url": ""}):
            with self.subTest(row=row):
                with (patch("agents.rag.retrieve_question.embed_texts", return_value=([VECTOR], {})),
                      patch("agents.rag.retrieve_question.search_festival_evidence", return_value=[row])):
                    with self.assertRaises(ValueError):
                        retrieve_festival_question(
                            object(), festival_id=FESTIVAL_ID, question="언제 시작하나요?",
                            as_of=AS_OF, embedding_version="official-v1", api_key="test-key",
                        )

    def test_invalid_context_stops_before_embedding(self):
        with patch("agents.rag.retrieve_question.embed_texts") as embed:
            for question in (" ", "가" * 501):
                with self.assertRaises(ValueError):
                    retrieve_festival_question(
                        object(), festival_id=FESTIVAL_ID, question=question, as_of=AS_OF,
                        embedding_version="official-v1", api_key="test-key",
                    )
            embed.assert_not_called()

    def test_embedding_adapter_preserves_input_order_and_dimension(self):
        body = {"data": [
            {"index": 1, "embedding": [2.0] * 1024},
            {"index": 0, "embedding": [1.0] * 1024},
        ], "usage": {"total_tokens": 7}}
        with patch("agents.rag.embedding.urllib.request.urlopen",
                   return_value=io.BytesIO(json.dumps(body).encode("utf-8"))) as urlopen:
            vectors, usage = embed_texts(["첫 질문", "둘째 질문"], "test-key")
        self.assertEqual([vector[0] for vector in vectors], [1.0, 2.0])
        self.assertEqual(usage, {"total_tokens": 7})
        sent = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(sent["dimensions"], 1024)
        self.assertEqual(sent["model"], "text-embedding-3-small")

    def test_embedding_adapter_rejects_wrong_dimension(self):
        body = {"data": [{"index": 0, "embedding": [1.0]}]}
        with patch("agents.rag.embedding.urllib.request.urlopen",
                   return_value=io.BytesIO(json.dumps(body).encode("utf-8"))):
            with self.assertRaises(ValueError):
                embed_texts(["질문"], "test-key")


if __name__ == "__main__":
    unittest.main()
