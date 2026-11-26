import unittest

from agents.rag.answer_question import answer_from_retrieval


class AnswerFromRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.retrieval = {"status": "candidates", "festival_id": "F01", "candidates": [
            {"festival_id": "F01", "document_id": "D1", "source_url": "https://official.example/f01",
             "content": "행사는 12월 11일 시작합니다."}]}
        self.kwargs = {"selected_festival_name": "서울빛초롱축제", "question": "언제 시작해요?"}

    def test_answer_keeps_official_source(self):
        result = answer_from_retrieval(self.retrieval, **self.kwargs,
            generate=lambda *_: {"decision": "answer", "answer": "12월 11일입니다.", "citation_ids": ["D1"]})
        self.assertEqual(result["source_urls"], ["https://official.example/f01"])

    def test_no_evidence_does_not_generate(self):
        result = answer_from_retrieval({"status": "no_evidence", "festival_id": "F01", "candidates": []},
            **self.kwargs, generate=lambda *_: self.fail("must not generate"))
        self.assertEqual(result["decision"], "abstain")

    def test_other_festival_name_does_not_generate(self):
        result = answer_from_retrieval(self.retrieval, selected_festival_name="서울빛초롱축제",
            question="청계천의 빛은 언제 끝나요?", other_festival_names=("청계천의 빛",),
            generate=lambda *_: self.fail("must not generate"))
        self.assertEqual(result["decision"], "abstain")

    def test_unapproved_citation_is_rejected(self):
        with self.assertRaises(ValueError):
            answer_from_retrieval(self.retrieval, **self.kwargs,
                generate=lambda *_: {"decision": "answer", "answer": "12월 12일", "citation_ids": ["D2"]})

    def test_conflicting_dates_can_abstain(self):
        result = answer_from_retrieval(self.retrieval, **self.kwargs,
            generate=lambda *_: {"decision": "abstain", "answer": "시작일 자료가 충돌해 확인할 수 없습니다.", "citation_ids": []})
        self.assertEqual(result["source_urls"], [])


if __name__ == "__main__":
    unittest.main()
