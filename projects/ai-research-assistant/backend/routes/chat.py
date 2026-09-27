"""Chat API route handling query generation and conversation chat orchestration."""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.chat_service import default_chat_service
from backend.dependencies import get_current_user

router = APIRouter()
chat_service = default_chat_service


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Execute chat query via ChatService layer with conversation management and error handling."""
    try:
        message = request.get_message()
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail=str(val_err)
        ) from val_err

    try:
        result = chat_service.chat(
            db=db,
            user_id=user_id,
            message=message,
            conversation_id=request.conversation_id,
            filename=request.filename
        )
        return ChatResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(exc)}"
        ) from exc
