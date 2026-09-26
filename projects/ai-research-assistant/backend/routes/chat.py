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
            filename=request.filename,
            conversation_id=request.conversation_id
        )

        return ChatResponse(
            answer=result["answer"],
            sources=result.get("sources", []),
            citation_map=result.get("citation_map"),
            invalid_citations=result.get("invalid_citations", []),
            document_sources=result.get("document_sources", []),
            subqueries=result.get("subqueries"),
            expanded_queries=result.get("expanded_queries"),
            used_hyde=result.get("used_hyde"),
            query_type=result.get("query_type"),
            query=result.get("query"),
            conversation_id=result.get("conversation_id"),
            user_id=user_id,
            latency_ms=result.get("latency_ms")
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="AI processing failed."
        ) from exc
