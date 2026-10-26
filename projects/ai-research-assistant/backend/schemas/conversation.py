"""Pydantic schemas for Conversation lifecycle and pagination."""


from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    title: str | None = None


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    conversation_id: int | None = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    title: str | None = None
    user_id: str | None = None
    messages: list[MessageResponse] | None = None

    class Config:
        from_attributes = True


class ConversationMessagesPageResponse(BaseModel):
    messages: list[MessageResponse] = Field(default_factory=list)
    limit: int
    offset: int
    has_more: bool
