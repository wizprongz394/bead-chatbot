"""In-memory TF-IDF vector store.

The previous version loaded a precomputed embeddings.npz built with
sentence-transformers (384-dim). Since we swapped to TF-IDF for Vercel
(4096-dim), the stored matrix is now incompatible.

Instead of loading a file, we fit TF-IDF on the embedded corpus once
at module import and keep the normalized matrix in memory. Queries are
transformed with the same fitted vectorizer, guaranteeing dimensional
consistency.
"""
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.knowledge.corpus import CORPUS


_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "at",
    "is", "are", "was", "were", "be", "been", "being", "with", "by",
    "as", "that", "this", "these", "those", "it", "its", "do", "does",
    "did", "can", "could", "would", "should", "will", "i", "you", "we",
    "they", "he", "she", "what", "which", "who", "when", "where", "why",
    "how", "your", "our", "their", "my", "me", "us", "them",
}


def _keywords(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return set(w for w in words if w not in _STOPWORDS and len(w) > 2)


# Fit once at module import
_VECTORIZER = TfidfVectorizer(max_features=4096, ngram_range=(1, 2), stop_words="english")
_TEXTS = [c["text"] for c in CORPUS if c.get("text")]
_MATRIX = _VECTORIZER.fit_transform(_TEXTS).toarray().astype(np.float32)
_norms = np.linalg.norm(_MATRIX, axis=1, keepdims=True)
_norms[_norms == 0] = 1
_MATRIX = _MATRIX / _norms


def search(query_vector, top_k=5):
    """
    query_vector: list[float] of dimension matching the fitted vectorizer.
    Returns list of dicts: {text, source_url, source_title, content_type, score}.
    """
    q = np.array(query_vector, dtype=np.float32).flatten()
    n = np.linalg.norm(q)
    if n > 0:
        q = q / n
    # Guard: if dims mismatch, truncate to the smaller for graceful degradation
    if q.shape[0] != _MATRIX.shape[1]:
        min_dim = min(q.shape[0], _MATRIX.shape[1])
        q = q[:min_dim]
        m = _MATRIX[:, :min_dim]
    else:
        m = _MATRIX
    scores = m @ q
    idx = np.argsort(-scores)[:top_k]
    results = []
    for i in idx:
        c = CORPUS[int(i)]
        results.append({
            "text": c["text"],
            "source_url": c["source_url"],
            "source_title": c["source_title"],
            "content_type": c["content_type"],
            "score": float(scores[int(i)]),
        })
    return results


def rerank(query, results, top_k=4):
    q_kw = _keywords(query)
    for r in results:
        c_kw = _keywords(r["text"])
        overlap = len(q_kw & c_kw) / max(len(q_kw), 1)
        boost = 0.15 if r.get("content_type") == "blog" else 0.0
        r["_rerank_score"] = 0.6 * r["score"] + 0.4 * overlap + boost
    results.sort(key=lambda r: -r["_rerank_score"])
    return results[:top_k]
