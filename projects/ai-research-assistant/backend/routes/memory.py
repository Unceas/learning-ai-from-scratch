"""Memory API route handling long-term memory creation and retrieval endpoints."""

from fastapi import APIRouter
from backend.schemas.requests import MemoryRequest
from backend.services.memory_service import store_user_memory, retrieve_user_memories, delete_user_memories

router = APIRouter()


@router.post("/")
def create_memory(request: MemoryRequest):
    """Store a memory snippet using memory_service."""
    result = store_user_memory(
        text=request.text,
        memory_type=request.memory_type,
        user_id=request.user_id or "default_user"
    )
    return result


@router.get("/")
def get_memories(query: str = "", user_id: str = "default_user"):
    """Retrieve filtered user memories."""
    memories = retrieve_user_memories(query=query, user_id=user_id)
    return {
        "user_id": user_id,
        "memories": memories
    }


@router.delete("/")
def clear_memories(user_id: str = "default_user"):
    """Delete long-term memory for user_id."""
    return delete_user_memories(user_id=user_id)
