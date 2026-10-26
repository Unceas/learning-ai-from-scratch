"""Pydantic schemas for API request and response validation."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    user_id: str | None = None
    username: str | None = None
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
    user_id: str | None = None
    username: str | None = None
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
    filename: str | None = None
    user_id: str | None = None
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Any] = []
    citation_map: dict[str, Any] | None = None
    invalid_citations: list[str] | None = []
    document_sources: list[dict[str, Any]] | None = None
    user_id: str | None = None
    latency_ms: float | None = None
    subqueries: list[str] | None = None
    expanded_queries: list[str] | None = None
    used_hyde: bool | None = None
    query_type: str | None = None
    query: Any | None = None
    conversation_id: int | None = None


class MemoryRequest(BaseModel):
    text: str = Field(min_length=1)
    memory_type: str | None = "general"
    user_id: str | None = None
