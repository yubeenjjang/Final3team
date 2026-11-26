"""OpenAI embedding adapter shared by RAG evaluation and retrieval."""

from __future__ import annotations

import json
import math
import urllib.request


MODEL = "text-embedding-3-small"
DIMENSIONS = 1024


def embed_texts(texts: list[str], api_key: str) -> tuple[list[list[float]], dict]:
    """Return vectors in input order; do not store or log the API key."""
    if not texts or any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError("embedding input must contain nonempty text")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("OpenAI API key is required")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=json.dumps({"model": MODEL, "dimensions": DIMENSIONS, "input": texts},
                        ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    vectors = [item["embedding"] for item in sorted(body["data"], key=lambda item: item["index"])]
    if (len(vectors) != len(texts)
            or any(len(vector) != DIMENSIONS or not all(math.isfinite(value) for value in vector)
                   for vector in vectors)):
        raise ValueError("Embedding count, dimension, or values differ from the requested setting")
    return vectors, body.get("usage", {})
