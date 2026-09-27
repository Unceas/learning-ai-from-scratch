"""Pydantic schemas for Conversation lifecycle and pagination."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: Optional[str] = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    conversation_id: Optional[int] = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    title: Optional[str] = None
    user_id: Optional[str] = None
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True


class ConversationMessagesPageResponse(BaseModel):
    messages: List[MessageResponse] = Field(default_factory=list)
    limit: int
    offset: int
    has_more: bool
