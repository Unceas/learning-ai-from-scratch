"""Pydantic schemas for API request and response validation."""

from typing import Optional, List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    filename: Optional[str] = None
    user_id: Optional[str] = "development-user"


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    user_id: Optional[str] = None
    latency_ms: Optional[float] = None


class MemoryRequest(BaseModel):
    text: str = Field(min_length=1)
    memory_type: Optional[str] = "general"
    user_id: Optional[str] = "development-user"
