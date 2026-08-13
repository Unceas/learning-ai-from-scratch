"""Chat API route handling query generation endpoints."""

from fastapi import APIRouter
from backend.schemas.requests import ChatRequest
from backend.services.rag_service import run_rag_pipeline

router = APIRouter()


@router.post("/")
def chat(request: ChatRequest):
    """Execute chat query via RAG service layer."""
    result = run_rag_pipeline(
        query=request.query,
        filename=request.filename,
        user_id=request.user_id or "default_user"
    )
    return result
