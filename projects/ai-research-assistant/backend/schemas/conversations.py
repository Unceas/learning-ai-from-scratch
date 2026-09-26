"""Pydantic schemas for Conversation Memory and Conversational RAG endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.schemas.rag import Source


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    title: Optional[str] = None


class ConversationMessageCreate(BaseModel):
    """Schema for posting a new user message within a conversation."""
    message: str = Field(min_length=1, max_length=5000)
    filename: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema representing an individual stored message."""
    id: int
    conversation_id: int
    role: str
    content: str

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Schema representing a conversation record with its messages."""
    id: int
    user_id: str
    title: Optional[str] = None
    messages: List[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ConversationChatResponse(BaseModel):
    """Schema representing response from sending a message to a conversation."""
    answer: str
    sources: List[Source] = Field(default_factory=list)
    query: Dict[str, str] = Field(
        ...,
        description="Query provenance tracking original and rewritten queries"
    )
    conversation_id: int
    citation_map: Optional[Dict[str, Any]] = None
    invalid_citations: Optional[List[str]] = Field(default_factory=list)
    subqueries: Optional[List[str]] = Field(default_factory=list)
    expanded_queries: Optional[List[str]] = Field(default_factory=list)
    used_hyde: Optional[bool] = False
    user_id: Optional[str] = None
