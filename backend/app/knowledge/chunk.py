"""Simple character-window chunker with metadata."""

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source_url: str
    source_title: str
    content_type: str
    chunk_index: int
    total_chunks: int


def chunk_text(
    text: str,
    source_url: str,
    source_title: str,
    content_type: str,
    target_chars: int = 1500,
    overlap_chars: int = 200,
):
    if not text:
        return []
    chunks = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + target_chars, n)
        if end < n:
            nl = text.rfind("\n", start, end)
            if nl > start + target_chars // 2:
                end = nl
        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(
                text=chunk_text,
                source_url=source_url,
                source_title=source_title,
                content_type=content_type,
                chunk_index=idx,
                total_chunks=0,
            ))
            idx += 1
        start = end - overlap_chars if end < n else n

    for c in chunks:
        c.total_chunks = len(chunks)
    return chunks
