def validate_review(review: dict, min_score: int = 7) -> bool:
    """Validate review result dictionary and evaluate pass threshold."""
    if not isinstance(review, dict):
        return False

    approved = review.get("approved", False)
    score = review.get("score", 0)

    return approved and (score >= min_score)
