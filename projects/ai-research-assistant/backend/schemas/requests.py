"""Pydantic schemas for API request and response validation."""

from typing import Optional, List
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    user_id: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    user_id: str
    password: str


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    filename: Optional[str] = None
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    user_id: Optional[str] = None
    latency_ms: Optional[float] = None


class MemoryRequest(BaseModel):
    text: str = Field(min_length=1)
    memory_type: Optional[str] = "general"
    user_id: Optional[str] = None
