"""Cross-Encoder re-ranking module for second-stage passage relevance scoring."""

from typing import Any, Dict, List
from sentence_transformers import CrossEncoder

# Initialize CrossEncoder model
reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(query: str, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Re-rank candidate context chunks using the CrossEncoder model.

    Args:
        query: User search query.
        retrieved_chunks: List of candidate chunk dictionaries.

    Returns:
        List of chunk dictionaries sorted by cross-encoder score descending, with 'rerank_score' included.
    """
    if not retrieved_chunks or not query.strip():
        return []

    pairs = [
        (query, chunk.get("text", ""))
        for chunk in retrieved_chunks
    ]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(scores, retrieved_chunks),
        reverse=True,
        key=lambda x: x[0]
    )

    result_chunks = []
    for score, chunk in ranked:
        updated_chunk = dict(chunk)
        updated_chunk["rerank_score"] = float(score)
        result_chunks.append(updated_chunk)

    return result_chunks
