"""Pydantic schemas for API request validation."""

from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    filename: Optional[str] = None
    user_id: Optional[str] = "default_user"


class MemoryRequest(BaseModel):
    text: str
    memory_type: Optional[str] = "general"
    user_id: Optional[str] = "default_user"
