"""Memory Service encapsulating user-isolated long-term memory operations."""

from typing import Dict, Any, List, Optional
from memory_store import search_memory, clear_memory
from memory_manager import default_memory_manager


def store_user_memory(text: str, memory_type: Optional[str] = "general", user_id: str = "default_user") -> Dict[str, Any]:
    """Store a memory snippet using MemoryManager deduplication and importance scoring."""
    status = default_memory_manager.remember(user_id, text, memory_type=memory_type)
    return {
        "status": status,
        "text": text,
        "user_id": user_id
    }


def retrieve_user_memories(query: str, user_id: str = "default_user", top_k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve filtered long-term memories for a user."""
    raw_memories = search_memory(user_id, query, top_k=top_k)
    return default_memory_manager.filter_memories(raw_memories, minimum_importance=0.4)


def delete_user_memories(user_id: str = "default_user") -> Dict[str, Any]:
    """Scoped deletion of user memories."""
    clear_memory(user_id=user_id)
    return {
        "status": "cleared",
        "user_id": user_id
    }
