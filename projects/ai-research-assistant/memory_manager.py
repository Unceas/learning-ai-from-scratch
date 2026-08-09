"""Memory manager controlling lifecycle, deduplication, importance scoring, and relevance filtering."""

from memory_store import add_memory, search_memory, collection, model
from memory_scoring import calculate_importance, categorize_memory_type


class MemoryManager:

    def __init__(self, deduplication_threshold: float = 0.85, minimum_importance: float = 0.4):
        self.deduplication_threshold = deduplication_threshold
        self.minimum_importance = minimum_importance

    def is_duplicate(self, text: str, threshold: float = None) -> bool:
        """Check if a semantic or exact duplicate memory already exists."""
        thresh = threshold if threshold is not None else self.deduplication_threshold

        if collection.count() == 0 or not text or not text.strip():
            return False

        embedding = model.encode([text]).tolist()[0]
        result = collection.query(
            query_embeddings=[embedding],
            n_results=1
        )

        if not result or not result.get("distances") or not result["distances"][0]:
            return False

        existing_text = result["documents"][0][0]
        if existing_text.lower().strip() == text.lower().strip():
            return True

        distance = result["distances"][0][0]
        # In cosine / L2 distance metrics, distance < (1.0 - threshold) indicates high similarity
        return distance < (1.0 - thresh)

    def remember(self, text: str, memory_type: str = None) -> str:
        """Process and conditionally store a new long-term memory."""
        if not text or not text.strip():
            return "Empty text ignored."

        if self.is_duplicate(text):
            return "Duplicate memory ignored."

        importance = calculate_importance(text)
        m_type = memory_type or categorize_memory_type(text)

        add_memory(
            text,
            importance=importance,
            memory_type=m_type
        )
        return "Memory stored."

    def filter_memories(self, memories: list, minimum_importance: float = None) -> list:
        """Filter retrieved memories by minimum importance threshold."""
        min_imp = minimum_importance if minimum_importance is not None else self.minimum_importance
        return [
            memory for memory in memories
            if isinstance(memory, dict) and memory.get("importance", 0.5) >= min_imp
        ]


default_memory_manager = MemoryManager()
