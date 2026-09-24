"""Reciprocal Rank Fusion (RRF) module for combining diverse retrieval result lists."""

from typing import Any, Dict, List, Tuple, Union


def _extract_chunk_key(chunk: Any) -> Any:
    """Derive deterministic identity key for a chunk across dicts and objects."""
    if hasattr(chunk, "document_id") and getattr(chunk, "document_id") is not None:
        doc_id = getattr(chunk, "document_id")
        c_idx = getattr(chunk, "chunk_index", getattr(chunk, "chunk_id", getattr(chunk, "chunk", 0)))
        return (doc_id, c_idx)

    if isinstance(chunk, dict):
        doc_id = chunk.get("document_id")
        c_idx = chunk.get("chunk_index", chunk.get("chunk_id", chunk.get("chunk", 0)))
        if doc_id is not None:
            return (doc_id, c_idx)
        if chunk.get("filename"):
            return (chunk.get("filename"), c_idx)
        if chunk.get("id"):
            return chunk.get("id")
        return chunk.get("text", "")[:100]

    if isinstance(chunk, (str, int)):
        return chunk

    if hasattr(chunk, "id") and getattr(chunk, "id") is not None:
        return getattr(chunk, "id")

    return id(chunk)


def reciprocal_rank_fusion(
    result_lists: List[List[Any]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """Combine and rank multiple retrieval result sets using Reciprocal Rank Fusion (RRF).

    Scores are calculated as: score = sum(1.0 / (k + rank)) across all result lists.

    Args:
        result_lists: Collection of ranked result lists. Each item can be a dict with
                      a 'chunk' key ({"chunk": ..., "score": ...}) or a direct chunk object/dict.
        k: Smoothing constant (default 60).

    Returns:
        List of dictionaries sorted descending by RRF score:
        [{"chunk": items[key], "score": score}, ...]
    """
    scores: Dict[Any, float] = {}
    items: Dict[Any, Any] = {}

    for results in result_lists:
        if not results:
            continue
        for rank, result in enumerate(results, start=1):
            if isinstance(result, dict) and "chunk" in result:
                chunk = result["chunk"]
            else:
                chunk = result

            key = _extract_chunk_key(chunk)

            scores[key] = scores.get(key, 0.0) + (1.0 / (k + rank))

            if key not in items:
                items[key] = dict(chunk) if isinstance(chunk, dict) else chunk
            else:
                # Merge metadata when combining duplicate records
                existing = items[key]
                if isinstance(existing, dict) and isinstance(chunk, dict):
                    # Preserve vector score if available
                    if "vector_score" in chunk and "vector_score" not in existing:
                        existing["vector_score"] = chunk["vector_score"]
                    # Merge matched subqueries
                    if "matched_queries" in chunk:
                        existing_matches = existing.get("matched_queries", [])
                        for mq in chunk["matched_queries"]:
                            if mq not in existing_matches:
                                existing_matches.append(mq)
                        existing["matched_queries"] = existing_matches

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    fused_results = []
    for key, score in ranked:
        item = items[key]
        if isinstance(item, dict):
            item_copy = dict(item)
            item_copy["score"] = score
            item_copy["rrf_score"] = score
            fused_results.append({
                "chunk": item_copy,
                "score": score,
            })
        else:
            fused_results.append({
                "chunk": item,
                "score": score,
            })

    return fused_results
