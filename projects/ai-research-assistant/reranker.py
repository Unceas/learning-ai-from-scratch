"""Cross-Encoder re-ranking module for second-stage passage relevance scoring."""

from typing import Any, Dict, List

_reranker_instance = None


def get_reranker():
    global _reranker_instance
    if _reranker_instance is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker_instance = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception:
            _reranker_instance = False
    return _reranker_instance if _reranker_instance is not False else None


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

    model_instance = get_reranker()
    if not model_instance:
        return [dict(c, rerank_score=0.5) for c in retrieved_chunks]

    pairs = [
        (query, chunk.get("text", ""))
        for chunk in retrieved_chunks
    ]

    try:
        scores = model_instance.predict(pairs)
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
    except Exception:
        return [dict(c, rerank_score=0.5) for c in retrieved_chunks]
