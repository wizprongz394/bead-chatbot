"""Loads embeddings + chunk metadata, provides cosine search and rerank."""
import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.config import DATA_DIR

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being", "with", "by",
    "as", "that", "this", "these", "those", "it", "its", "do", "does",
    "did", "can", "could", "would", "should", "will", "i", "you", "we",
    "they", "he", "she", "what", "which", "who", "when", "where", "why",
    "how", "your", "our", "their", "my", "me", "us", "them"
}


@lru_cache(maxsize=1)
def _load():
    npz_path = DATA_DIR / "embeddings.npz"
    meta_path = DATA_DIR / "chunk_metadata.jsonl"
    if not npz_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            "Vector store not found. Run `python -m app.knowledge.run_ingest` first."
        )
    data = np.load(npz_path)
    embeddings = data["embeddings"]
    chunks = []
    with meta_path.open("r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return embeddings, chunks


def search(query_vector, top_k=5):
    embeddings, chunks = _load()
    q = np.array(query_vector, dtype=np.float32)
    n = np.linalg.norm(q)
    if n > 0:
        q = q / n
    scores = embeddings @ q
    idx = np.argsort(-scores)[:top_k]
    results = []
    for i in idx:
        c = chunks[int(i)]
        results.append({
            "text": c["text"],
            "source_url": c["source_url"],
            "source_title": c["source_title"],
            "content_type": c["content_type"],
            "score": float(scores[int(i)]),
        })
    return results


def _keywords(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in _STOPWORDS and len(w) > 2)


def rerank(query, results, top_k=4):
    q_kw = _keywords(query)
    for r in results:
        c_kw = _keywords(r["text"])
        overlap = len(q_kw & c_kw) / max(len(q_kw), 1)
        boost = 0.15 if r.get("content_type") == "blog" else 0.0
        r["_rerank_score"] = 0.6 * r["score"] + 0.4 * overlap + boost
    results.sort(key=lambda r: -r["_rerank_score"])
    return results[:top_k]
