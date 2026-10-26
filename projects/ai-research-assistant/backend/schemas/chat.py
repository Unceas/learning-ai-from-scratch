"""Pydantic schemas for Chat Service and /api/chat endpoints."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: str | None = None
    query: str | None = None
    conversation_id: int | None = None
    filename: str | None = None
    user_id: str | None = None

    @model_validator(mode="after")
    def validate_content(self) -> "ChatRequest":
        text = self.message if self.message is not None else self.query
        if text is None or not text.strip():
            raise ValueError("Query or message text cannot be empty.")
        if len(text.strip()) > 5000:
            raise ValueError("Query or message text exceeds maximum length of 5000 characters.")
        return self

    def get_message(self) -> str:
        """Resolve message text from either 'message' or 'query' field."""
        text = self.message if self.message is not None else self.query
        if not text or not text.strip():
            raise ValueError("Message text cannot be empty.")
        return text.strip()


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int | None = None
    answer: str
    sources: list[Any] = Field(default_factory=list)
    rewritten_query: str = ""
    # Backwards compatibility fields for earlier test suites
    query: Any | None = None
    citation_map: dict[str, Any] | None = None
    invalid_citations: list[str] | None = Field(default_factory=list)
    document_sources: list[dict[str, Any]] | None = None
    user_id: str | None = None
    latency_ms: float | None = None
    subqueries: list[str] | None = None
    expanded_queries: list[str] | None = None
    used_hyde: bool | None = None
    query_type: str | None = None
    metrics: dict[str, Any] | None = None
