"""Chat API route handling query generation endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from backend.schemas.requests import ChatRequest, ChatResponse
from backend.services.agent_service import AgentService
from backend.dependencies import get_current_user

router = APIRouter()
agent_service = AgentService()


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    """Execute chat query via AgentService layer with error handling and request validation."""
    try:
        result = agent_service.run(
            query=request.query,
            user_id=user_id,
            filename=request.filename
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            user_id=user_id,
            latency_ms=result.get("latency_ms")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="AI processing failed."
        ) from exc
