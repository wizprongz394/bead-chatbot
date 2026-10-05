"""Embedding via TF-IDF. No torch, no transformers.

Used in production (Vercel) where the sentence-transformers bundle
would exceed the 500 MB function size limit. Retrieval quality is
lower than neural embeddings but works for a corpus our size.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

_VECTORIZER = None
_MATRIX = None


def _fit(texts):
    global _VECTORIZER, _MATRIX
    _VECTORIZER = TfidfVectorizer(
        max_features=4096,
        ngram_range=(1, 2),
        stop_words="english",
    )
    _MATRIX = _VECTORIZER.fit_transform(texts).toarray().astype(np.float32)
    norms = np.linalg.norm(_MATRIX, axis=1, keepdims=True)
    norms[norms == 0] = 1
    _MATRIX = _MATRIX / norms


def embed_texts(texts):
    """
    Two modes:
    - First call with a large list (corpus) -> fits TF-IDF.
    - Later calls with a single query -> transforms only.
    Uses a heuristic: if we've never fit before, or if the list is long, fit.
    """
    global _VECTORIZER, _MATRIX
    if _VECTORIZER is None or len(texts) > 10:
        _fit(texts)
        return _MATRIX.tolist()
    # Query mode
    vec = _VECTORIZER.transform(texts).toarray().astype(np.float32)
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (vec / norms).tolist()


def load_pretrained():
    """Re-fit on the stored corpus. Called once at startup in production."""
    import json
    from app.config import DATA_DIR

    path = DATA_DIR / "content_chunks.jsonl"
    texts = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                texts.append(json.loads(line)["text"])
            except Exception:
                pass
    if texts:
        _fit(texts)
