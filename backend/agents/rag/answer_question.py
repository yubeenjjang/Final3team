"""Turn approved retrieval candidates into a source-checked answer decision.

The caller supplies the answer generator. This module does not approve sources or
make an LLM request; it enforces the retrieval boundary around that request.
"""

from __future__ import annotations

from typing import Callable


def answer_from_retrieval(
    retrieval: dict,
    *,
    selected_festival_name: str,
    question: str,
    generate: Callable[[str, str, list[dict]], dict],
    other_festival_names: tuple[str, ...] = (),
) -> dict:
    """Return an answer only when its citations point to retrieved evidence."""
    festival_id = retrieval.get("festival_id")
    if not isinstance(festival_id, str) or not festival_id:
        raise ValueError("retrieval must identify the selected festival")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question is required")
    if not isinstance(selected_festival_name, str) or not selected_festival_name.strip():
        raise ValueError("selected_festival_name is required")
    if any(name and name != selected_festival_name and name in question for name in other_festival_names):
        return _abstain("질문한 축제가 현재 선택한 축제와 다릅니다. 축제를 다시 선택해 주세요.")
    candidates = retrieval.get("candidates")
    if retrieval.get("status") == "no_evidence" and candidates == []:
        return _abstain("유효한 공식 안내 근거를 찾지 못했습니다.")
    if retrieval.get("status") != "candidates" or not isinstance(candidates, list) or not candidates:
        raise ValueError("invalid retrieval status or candidates")
    sources = {}
    for candidate in candidates:
        if (candidate.get("festival_id") != festival_id
                or not isinstance(candidate.get("document_id"), str)
                or not isinstance(candidate.get("source_url"), str)
                or not candidate["source_url"].startswith("https://")
                or not isinstance(candidate.get("content"), str) or not candidate["content"].strip()):
            raise ValueError("candidate is missing selected festival evidence")
        doc_id = candidate["document_id"]
        if doc_id in sources and sources[doc_id] != candidate["source_url"]:
            raise ValueError("document has conflicting source URLs")
        sources[doc_id] = candidate["source_url"]
    decision = generate(question, selected_festival_name, candidates)
    if not isinstance(decision, dict) or decision.get("decision") not in {"answer", "abstain"}:
        raise ValueError("invalid answer decision")
    answer = decision.get("answer")
    citations = decision.get("citation_ids")
    if not isinstance(answer, str) or not answer.strip() or not isinstance(citations, list):
        raise ValueError("answer or citations missing")
    if decision["decision"] == "abstain":
        if citations:
            raise ValueError("abstention must not cite documents")
        return _abstain(answer)
    if not citations or any(not isinstance(ref, str) or ref not in sources for ref in citations):
        raise ValueError("answer cites unapproved or missing evidence")
    return {"decision": "answer", "answer": answer, "citation_ids": citations,
            "source_urls": [sources[ref] for ref in dict.fromkeys(citations)]}


def _abstain(message: str) -> dict:
    return {"decision": "abstain", "answer": message, "citation_ids": [], "source_urls": []}
