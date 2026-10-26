"""Evaluation metrics for RAG retrieval quality, citation validity, and grounding."""

import re
from collections.abc import Sequence
from typing import Any

from backend.evaluation.generation_metrics import citation_precision, evaluate_grounding
from backend.evaluation.retrieval_metrics import mean_recall, recall_at_k


def citation_validity(answer: str, valid_ids: set[str] | Sequence[str]) -> float:
    """Measure proportion of generated citations [S#] that reference verified source IDs.

    Args:
        answer: Model-generated answer text containing potential citation tags.
        valid_ids: Collection of valid source identifiers (e.g. {'S1', 'S2'} or {1, 2}).

    Returns:
        Float ratio between 0.0 and 1.0. Returns 0.0 if no citations exist.
    """
    citations = re.findall(r"\[S(\d+)\]", answer)
    if not citations:
        return 0.0

    # Normalize valid IDs to both 'S#' and '#' forms for flexibility
    normalized_valid = set()
    for vid in valid_ids:
        s_str = str(vid).strip()
        normalized_valid.add(s_str if s_str.startswith("S") else f"S{s_str}")

    valid_count = sum(
        f"S{citation}" in normalized_valid
        for citation in citations
    )

    return valid_count / len(citations)


def citation_coverage(answer: str, expected_citations: int = 1) -> float:
    """Calculate the coverage of citations in answers that require evidence.

    Args:
        answer: Generated text.
        expected_citations: Minimum expected citations.

    Returns:
        Score between 0.0 and 1.0.
    """
    citations = re.findall(r"\[S(\d+)\]", answer)
    if expected_citations <= 0:
        return 1.0
    return min(1.0, len(citations) / expected_citations)


def calculate_rag_metrics(
    retrieved_docs: list[str],
    expected_docs: list[str],
    answer: str,
    valid_source_ids: set[str],
    latency_ms: float = 0.0,
    k: int = 5,
) -> dict[str, Any]:
    """Compute comprehensive metrics for an individual RAG evaluation query."""
    rec = recall_at_k(retrieved_docs, expected_docs, k=k)
    cit_val = citation_validity(answer, valid_source_ids)
    cit_prec = citation_precision(answer, valid_source_ids)

    return {
        "recall_at_k": rec,
        "citation_validity": cit_val,
        "citation_precision": cit_prec,
        "latency_ms": latency_ms,
        "has_citations": bool(re.search(r"\[S\d+\]", answer)),
    }


__all__ = [
    "calculate_rag_metrics",
    "citation_coverage",
    "citation_precision",
    "citation_validity",
    "evaluate_grounding",
    "mean_recall",
    "recall_at_k",
]
