"""Importance scoring and memory categorization module."""


def calculate_importance(text: str) -> float:
    """Calculate an importance score between 0.0 and 1.0 for a memory snippet."""
    if not text:
        return 0.3

    text_lower = text.lower()

    high_priority = [
        "remember",
        "always",
        "never",
        "my goal",
        "my project",
        "my preference",
        "i prefer"
    ]

    medium_priority = [
        "usually",
        "often",
        "working on",
        "learning"
    ]

    for keyword in high_priority:
        if keyword in text_lower:
            return 1.0

    for keyword in medium_priority:
        if keyword in text_lower:
            return 0.7

    return 0.3


def categorize_memory_type(text: str) -> str:
    """Categorize memory into general, preference, project, goal, or fact."""
    if not text:
        return "general"

    text_lower = text.lower()

    if any(k in text_lower for k in ["prefer", "preference", "always", "never", "like"]):
        return "preference"

    if any(k in text_lower for k in ["project", "building", "app", "system"]):
        return "project"

    if any(k in text_lower for k in ["goal", "aim", "trying to", "target"]):
        return "goal"

    if any(k in text_lower for k in ["fact", "i am", "name", "role", "my name"]):
        return "fact"

    return "general"
