"""Pydantic schemas for Answer Feedback endpoints."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for submitting or updating answer feedback."""
    message_id: int
    rating: Literal["helpful", "not_helpful"]
    reason: Optional[str] = None
    comment: Optional[str] = Field(
        default=None,
        max_length=2000,
    )


class FeedbackResponse(BaseModel):
    """Schema representing stored answer feedback."""
    id: int
    message_id: int
    rating: Literal["helpful", "not_helpful"]
    reason: Optional[str] = None
    comment: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackSummaryResponse(BaseModel):
    """Schema representing aggregated feedback metrics for a user."""
    helpful: int = 0
    not_helpful: int = 0
    total: int = 0
