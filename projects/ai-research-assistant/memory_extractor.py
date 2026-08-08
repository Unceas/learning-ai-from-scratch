"""Memory extraction rules and filtering logic for persistent memory storage."""


def should_store_memory(user_message: str, assistant_message: str) -> bool:
    """Evaluate whether a turn contains persistent preferences, facts, or explicit memory requests."""
    keywords = [
        "remember",
        "prefer",
        "always",
        "usually",
        "my project",
        "my goal",
        "i am",
        "i use",
        "i need"
    ]

    text = (
        (user_message or "").lower()
        + " "
        + (assistant_message or "").lower()
    )

    return any(
        keyword in text
        for keyword in keywords
    )


def extract_memory_snippet(user_message: str, assistant_message: str) -> str:
    """Extract a concise text snippet to represent the long-term memory."""
    return f"User preference / context: {user_message.strip()}"
