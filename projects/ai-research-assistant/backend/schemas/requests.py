"""Pydantic schemas for API request and response validation."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="before")
    @classmethod
    def populate_user(cls, data: Any):
        if isinstance(data, dict):
            uid = data.get("user_id") or data.get("username")
            if uid:
                data["user_id"] = str(uid).strip()
                data["username"] = str(uid).strip()
            elif not data.get("user_id"):
                raise ValueError("user_id or username is required.")
        return data


class LoginRequest(BaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    password: str

    @model_validator(mode="before")
    @classmethod
    def populate_user(cls, data: Any):
        if isinstance(data, dict):
            uid = data.get("user_id") or data.get("username")
            if uid:
                data["user_id"] = str(uid).strip()
                data["username"] = str(uid).strip()
            elif not data.get("user_id"):
                raise ValueError("user_id or username is required.")
        return data


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=5000)
    filename: Optional[str] = None
    user_id: Optional[str] = None
    conversation_id: Optional[int] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[Any] = []
    citation_map: Optional[Dict[str, Any]] = None
    invalid_citations: Optional[List[str]] = []
    document_sources: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = None
    latency_ms: Optional[float] = None
    subqueries: Optional[List[str]] = None
    expanded_queries: Optional[List[str]] = None
    used_hyde: Optional[bool] = None
    query_type: Optional[str] = None
    query: Optional[Any] = None
    conversation_id: Optional[int] = None


class MemoryRequest(BaseModel):
    text: str = Field(min_length=1)
    memory_type: Optional[str] = "general"
    user_id: Optional[str] = None
