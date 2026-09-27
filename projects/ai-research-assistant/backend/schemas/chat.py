"""Pydantic schemas for Chat Service and /api/chat endpoints."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    message: Optional[str] = None
    query: Optional[str] = None
    conversation_id: Optional[int] = None
    filename: Optional[str] = None
    user_id: Optional[str] = None

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
    answer: str
    sources: List[Any] = Field(default_factory=list)
    rewritten_query: str = ""
    # Backwards compatibility fields for earlier test suites
    query: Optional[Any] = None
    citation_map: Optional[Dict[str, Any]] = None
    invalid_citations: Optional[List[str]] = Field(default_factory=list)
    document_sources: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None
    latency_ms: Optional[float] = None
    subqueries: Optional[List[str]] = None
    expanded_queries: Optional[List[str]] = None
    used_hyde: Optional[bool] = None
    query_type: Optional[str] = None
