"""Text chunker module for word-based sliding window chunking."""

from typing import List


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text string into overlapping word chunks.

    Args:
        text: Input string content.
        chunk_size: Number of words per chunk.
        overlap: Overlapping word count between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0

    step = max(1, chunk_size - overlap)
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += step

    return chunks
