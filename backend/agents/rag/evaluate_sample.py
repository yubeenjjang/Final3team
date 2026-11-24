"""Small, isolated embedding smoke test for the W27 festival RAG decision.

This does not query PostgreSQL or test answer generation. It uses short,
paraphrased excerpts from the official pages listed in the W27 prep document.
"""

from __future__ import annotations

import argparse
import getpass
import json
import math
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


MODEL = "text-embedding-3-small"
DIMENSIONS = 1024
AS_OF = datetime.fromisoformat("2026-11-24T12:00:00+09:00")
OUTPUT = Path(__file__).with_name("sample_eval_results.json")
LANTERN_ID = "fst_01M835B57450M888RBNEFVRWWA"

DOCUMENTS = [
    {
        "id": "D1",
        "festival": LANTERN_ID,
        "text": "2026 서울빛초롱축제는 12월 11일부터 2027년 1월 31일까지 청계광장에서 삼일교까지 열린다. 관람 시간은 매일 18시부터 23시까지이며 무료다.",
        "effective_to": "2027-02-01T00:00:00+09:00",
        "source_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=983",
    },
    {
        "id": "D2",
        "festival": "fixture_seoul_winter",
        "text": "서울윈터페스티벌은 2026년 12월 11일부터 2027년 1월 31일까지 광화문광장 등 여러 장소에서 열린다. 서울빛초롱축제도 포함된 통합 축제다.",
        "effective_to": "2027-02-01T00:00:00+09:00",
        "source_url": "https://festival.seoul.go.kr/festival/main/festivalView.do?festacode=373",
    },
    {
        "id": "D3",
        "festival": "fixture_mokdong_bbq",
        "text": "2026 목동깨비시장 깨비야간 BBQ페스티벌은 원래 11월 14일에서 11월 21일로 변경되어 13시부터 21시까지 열렸다.",
        "effective_to": "2026-11-22T00:00:00+09:00",
        "source_url": "https://youth.seoul.go.kr/infoData/sprtInfo/view.do?key=2309130006&sprtInfoId=75640",
    },
]

QUESTIONS = [
    ("Q01", LANTERN_ID, "서울빛초롱축제는 언제 시작하나요?", "D1"),
    ("Q02", LANTERN_ID, "서울빛초롱축제는 어디에서 몇 시까지 볼 수 있나요?", "D1"),
    ("Q03", "fixture_seoul_winter", "서울윈터페스티벌은 어디에서 열리나요?", "D2"),
    ("Q04", "fixture_seoul_winter", "서울윈터페스티벌 기간은 언제인가요?", "D2"),
    ("Q05", LANTERN_ID, "서울윈터페스티벌의 다른 프로그램도 알려줘", None),
    ("Q06", "fixture_seoul_winter", "서울빛초롱축제 관람 시간은 몇 시인가요?", None),
    ("Q07", "fixture_mokdong_bbq", "2026년 11월 25일에 가도 축제를 즐길 수 있나요?", None),
    ("Q08", LANTERN_ID, "오늘 비 때문에 서울빛초롱축제가 취소됐나요?", None),
    ("Q09", LANTERN_ID, "지금 축제 주변은 얼마나 혼잡한가요?", None),
    ("Q10", LANTERN_ID, "유료 좌석을 예약할 수 있나요?", None),
]


def eligible_documents(festival: str) -> list[dict]:
    return [
        doc
        for doc in DOCUMENTS
        if doc["festival"] == festival
        and (
            doc["effective_to"] is None
            or AS_OF < datetime.fromisoformat(doc["effective_to"])
        )
    ]


def cosine(a: list[float], b: list[float]) -> float:
    numerator = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return numerator / (norm_a * norm_b)


def embed(texts: list[str], api_key: str) -> tuple[list[list[float]], dict]:
    payload = json.dumps(
        {"model": MODEL, "dimensions": DIMENSIONS, "input": texts},
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    vectors = [item["embedding"] for item in sorted(body["data"], key=lambda x: x["index"])]
    if len(vectors) != len(texts) or any(len(vector) != DIMENSIONS for vector in vectors):
        raise ValueError("Embedding count or dimension differs from the requested setting")
    return vectors, body.get("usage", {})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Prompt for a key and call OpenAI")
    args = parser.parse_args()

    print(f"Model: {MODEL}, dimensions: {DIMENSIONS}, as_of: {AS_OF.isoformat()}")
    for question_id, festival, _question, expected in QUESTIONS:
        eligible = [doc["id"] for doc in eligible_documents(festival)]
        print(f"{question_id}: eligible={eligible}, expected_evidence={expected or 'manual abstention check'}")
        if expected is not None and expected not in eligible:
            raise ValueError(f"{question_id}: expected document filtered out")
        if question_id == "Q07" and eligible:
            raise ValueError("Expired festival document was not filtered out")

    if not args.live:
        print("Metadata smoke test passed. No API call was made.")
        return 0

    api_key = getpass.getpass("OpenAI API key (hidden; not saved): ").strip()
    if not api_key:
        print("No API key entered; stopped before the API call.", file=sys.stderr)
        return 2
    texts = [doc["text"] for doc in DOCUMENTS] + [item[2] for item in QUESTIONS]
    try:
        vectors, usage = embed(texts, api_key)
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        print(f"Embedding request failed: {exc}", file=sys.stderr)
        return 1
    finally:
        api_key = ""

    doc_vectors = {doc["id"]: vectors[index] for index, doc in enumerate(DOCUMENTS)}
    results = []
    for index, (question_id, festival, question, expected) in enumerate(QUESTIONS):
        eligible = eligible_documents(festival)
        ranked = sorted(
            (
                {"document_id": doc["id"], "cosine_similarity": round(cosine(doc_vectors[doc["id"]], vectors[len(DOCUMENTS) + index]), 4)}
                for doc in eligible
            ),
            key=lambda item: item["cosine_similarity"],
            reverse=True,
        )
        result = {
            "question_id": question_id,
            "question": question,
            "eligible_document_ids": [doc["id"] for doc in eligible],
            "ranked": ranked,
            "expected_evidence": expected,
            "retrieval_match": ranked[0]["document_id"] == expected if expected and ranked else None,
        }
        results.append(result)
        print(f"{question_id}: ranked={ranked}, retrieval_match={result['retrieval_match']}")

    OUTPUT.write_text(
        json.dumps(
            {"model": MODEL, "dimensions": DIMENSIONS, "as_of": AS_OF.isoformat(), "usage": usage, "scope": "D1 public EV01; D2 and D3 isolated fixtures; no DB or answer generation", "results": results},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved results: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
