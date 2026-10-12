"""Database service for storing, updating, and aggregating answer feedback."""

from typing import Dict, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.models.feedback import AnswerFeedback
from backend.models.conversation import Conversation, ConversationMessage


def submit_feedback(
    db: Session,
    user_id: str,
    message_id: int,
    rating: str,
    reason: Optional[str] = None,
    comment: Optional[str] = None,
) -> AnswerFeedback:
    """Create or update answer feedback with strict ownership and assistant-role validation."""
    # 1. Verify message exists
    message = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.id == message_id)
        .first()
    )
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    # 2. Reject non-assistant messages
    if message.role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback can only be submitted for assistant messages.",
        )

    # 3. Verify conversation ownership
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == message.conversation_id,
            Conversation.user_id == user_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message or conversation not found.",
        )

    # 4. Upsert feedback record
    existing = (
        db.query(AnswerFeedback)
        .filter(AnswerFeedback.message_id == message_id)
        .first()
    )

    if existing:
        existing.rating = rating
        existing.reason = reason
        existing.comment = comment
        db.commit()
        db.refresh(existing)
        return existing

    feedback = AnswerFeedback(
        user_id=user_id,
        conversation_id=conversation.id,
        message_id=message.id,
        rating=rating,
        reason=reason,
        comment=comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback_by_message(
    db: Session,
    user_id: str,
    message_id: int,
) -> Optional[AnswerFeedback]:
    """Retrieve feedback for a specific message belonging to the authenticated user."""
    return (
        db.query(AnswerFeedback)
        .filter(
            AnswerFeedback.message_id == message_id,
            AnswerFeedback.user_id == user_id,
        )
        .first()
    )


def get_feedback_summary(
    db: Session,
    user_id: str,
) -> Dict[str, int]:
    """Aggregate answer feedback metrics for the authenticated user."""
    rows = (
        db.query(
            AnswerFeedback.rating,
            func.count(AnswerFeedback.id),
        )
        .filter(AnswerFeedback.user_id == user_id)
        .group_by(AnswerFeedback.rating)
        .all()
    )

    counts = {rating: count for rating, count in rows}
    return {
        "helpful": counts.get("helpful", 0),
        "not_helpful": counts.get("not_helpful", 0),
        "total": sum(counts.values()),
    }
