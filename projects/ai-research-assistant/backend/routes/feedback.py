"""Answer Feedback API route handling rating submission, retrieval, and aggregation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackSummaryResponse,
)
from backend.services.feedback_service import (
    get_feedback_by_message,
    get_feedback_summary,
)
from backend.services.feedback_service import (
    submit_feedback as save_feedback,
)

router = APIRouter()


@router.post("", response_model=FeedbackResponse, include_in_schema=False)
@router.post("/", response_model=FeedbackResponse)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Submit or update feedback for a persisted assistant message."""
    feedback = save_feedback(
        db=db,
        user_id=user_id,
        message_id=payload.message_id,
        rating=payload.rating,
        reason=payload.reason,
        comment=payload.comment,
    )
    return feedback


@router.get("/summary", response_model=FeedbackSummaryResponse)
def get_user_feedback_summary(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Retrieve feedback summary counts for the authenticated user."""
    return get_feedback_summary(db=db, user_id=user_id)


@router.get("/{message_id}", response_model=FeedbackResponse)
def get_message_feedback(
    message_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """Retrieve existing feedback for a specific assistant message."""
    feedback = get_feedback_by_message(
        db=db,
        user_id=user_id,
        message_id=message_id,
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this message.",
        )
    return feedback
