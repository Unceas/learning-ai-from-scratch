"""Pydantic schemas for Conversation Memory and Conversational RAG endpoints."""

from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.rag import Source


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    title: str | None = None


class ConversationMessageCreate(BaseModel):
    """Schema for posting a new user message within a conversation."""
    message: str = Field(min_length=1, max_length=5000)
    filename: str | None = None


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
    title: str | None = None
    messages: list[MessageResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ConversationMessagesPageResponse(BaseModel):
    """Schema representing paginated messages response."""
    messages: list[MessageResponse] = Field(default_factory=list)
    limit: int
    offset: int
    has_more: bool


class ConversationChatResponse(BaseModel):
    """Schema representing response from sending a message to a conversation."""
    answer: str
    message_id: int | None = None
    sources: list[Source] = Field(default_factory=list)
    query: dict[str, str] = Field(
        ...,
        description="Query provenance tracking original and rewritten queries"
    )
    conversation_id: int
    citation_map: dict[str, Any] | None = None
    invalid_citations: list[str] | None = Field(default_factory=list)
    subqueries: list[str] | None = Field(default_factory=list)
    expanded_queries: list[str] | None = Field(default_factory=list)
    used_hyde: bool | None = False
    user_id: str | None = None
