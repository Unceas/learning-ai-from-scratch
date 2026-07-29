"""Session-based conversation memory management for multi-turn RAG."""

from typing import Dict, List


class ConversationMemory:
    """Manages short-term conversation history for multi-turn interactions."""

    def __init__(self, max_turns: int = 5):
        """Initialize ConversationMemory with maximum history turn capacity.

        Args:
            max_turns: Maximum number of user-assistant turns to retain.
        """
        self.history: List[Dict[str, str]] = []
        self.max_turns: int = max_turns

    def add(self, user: str, assistant: str) -> None:
        """Add a user query and assistant response turn to memory.

        Args:
            user: User query text.
            assistant: Assistant response text.
        """
        self.history.append({
            "user": user,
            "assistant": assistant
        })

        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def context(self) -> str:
        """Format stored conversation history into a structured string context.

        Returns:
            Formatted conversation history.
        """
        conversation = ""

        for turn in self.history:
            conversation += (
                f"User: {turn['user']}\n"
                f"Assistant: {turn['assistant']}\n\n"
            )

        return conversation

    def clear(self) -> None:
        """Clear all stored conversation history."""
        self.history.clear()
