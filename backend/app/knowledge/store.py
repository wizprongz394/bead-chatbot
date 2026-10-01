"""
Write products and chunks to disk.
Uses a simple numpy-based vector store — no Chroma, no native deps.
For our corpus size (~50-500 chunks), this is faster and simpler than a real vector DB.
"""

import json
from pathlib import Path

import numpy as np

from app.config import DATA_DIR


def write_products(products):
    path = DATA_DIR / "products.json"
    path.write_text(json.dumps(products, indent=2), encoding="utf-8")
    return path


def write_chunks(chunks):
    path = DATA_DIR / "content_chunks.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({
                "text": c.text,
                "source_url": c.source_url,
                "source_title": c.source_title,
                "content_type": c.content_type,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
            }) + "\n")
    return path


def build_vector_store(chunks, embeddings):
    """
    Save chunks + embeddings as a numpy .npz file and a jsonl metadata file.
    At query time we load these and do cosine similarity manually.
    """
    matrix = np.array(embeddings, dtype=np.float32)

    # Normalize each vector to unit length for cosine similarity
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    normalized = matrix / norms

    # Save the matrix
    npz_path = DATA_DIR / "embeddings.npz"
    np.savez_compressed(npz_path, embeddings=normalized)

    # Save metadata alongside — one line per chunk, in the same order as the matrix
    meta_path = DATA_DIR / "chunk_metadata.jsonl"
    with meta_path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps({
                "text": c.text,
                "source_url": c.source_url,
                "source_title": c.source_title,
                "content_type": c.content_type,
                "chunk_index": c.chunk_index,
            }) + "\n")

    return npz_path, meta_path