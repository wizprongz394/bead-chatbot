"""Loads the corpus from a Python module instead of a JSONL file.

Vercel's Python bundler doesn't reliably include data files referenced
only at runtime via Path(). By embedding the corpus as Python literals
we eliminate the file dependency entirely.
"""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.knowledge.corpus import CORPUS  # list of dicts

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


def load_pretrained():
    """Fit TF-IDF on the embedded corpus. Called once at startup."""
    global _VECTORIZER, _MATRIX
    if _VECTORIZER is not None:
        return
    texts = [c["text"] for c in CORPUS if c.get("text")]
    if texts:
        _fit(texts)


def embed_texts(texts):
    """If we haven't fit yet, fit. Otherwise transform the query."""
    global _VECTORIZER, _MATRIX
    if _VECTORIZER is None:
        # Fit on the corpus + the given texts
        corpus_texts = [c["text"] for c in CORPUS if c.get("text")]
        if corpus_texts:
            _fit(corpus_texts)
            # Now transform the input
            vec = _VECTORIZER.transform(texts).toarray().astype(np.float32)
            norms = np.linalg.norm(vec, axis=1, keepdims=True)
            norms[norms == 0] = 1
            return (vec / norms).tolist()
        # Fallback: no corpus, just fit on the input
        _fit(texts)
        return _MATRIX.tolist()
    # Already fit — just transform
    vec = _VECTORIZER.transform(texts).toarray().astype(np.float32)
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (vec / norms).tolist()
