"""Retrieval evaluation metrics including Recall@K and Mean Recall@K."""

from typing import List, Sequence


def recall_at_k(
    retrieved_documents: Sequence[str],
    expected_documents: Sequence[str],
    k: int,
) -> float:
    """Calculate Recall@K proportion for expected documents.

    Args:
        retrieved_documents: List of retrieved filenames in rank order.
        expected_documents: List of ground-truth relevant document filenames.
        k: Maximum rank depth to evaluate.

    Returns:
        Recall score as a float between 0.0 and 1.0.
    """
    if k <= 0:
        return 0.0

    retrieved = set(retrieved_documents[:k])
    expected = set(expected_documents)

    if not expected:
        return 0.0

    return len(retrieved & expected) / len(expected)


def mean_recall(scores: Sequence[float]) -> float:
    """Calculate mean recall across a sequence of individual question recall scores.

    Args:
        scores: Sequence of floating-point recall values.

    Returns:
        Average recall score between 0.0 and 1.0.
    """
    if not scores:
        return 0.0

    return sum(scores) / len(scores)
