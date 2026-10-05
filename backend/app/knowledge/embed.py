"""Query-time embedding. Delegates to the shared vectorizer in vector_store.

Kept as a separate module so the engine can import a single embedding
function without knowing about the search internals.
"""
import numpy as np

from app.services.retrieval.vector_store import _VECTORIZER


def load_pretrained():
    """No-op. Fitting happens at vector_store import time."""
    return None


def embed_texts(texts):
    """Transform a list of strings into normalized TF-IDF vectors."""
    vec = _VECTORIZER.transform(texts).toarray().astype(np.float32)
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms[norms == 0] = 1
    return (vec / norms).tolist()
