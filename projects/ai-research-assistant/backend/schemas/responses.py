"""Pydantic schemas for API response validation and documentation contracts."""

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str


class DocumentResponse(BaseModel):
    status: str
    document_id: int | None = None
    id: int | None = None
    filename: str | None = None
    pages: int | None = None
    chunks: int | None = None
    error_message: str | None = None


class DocumentStatusResponse(BaseModel):
    id: int
    filename: str
    file_hash: str
    chunks: int
    status: str
    error_message: str | None = None
    processing_attempts: int | None = None


class DocumentListResponse(BaseModel):
    documents: list[dict[str, Any]]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    user_id: str | None = None


class ChunkPreviewResponse(BaseModel):
    id: str | None = None
    document_id: int
    filename: str
    chunk_index: int
    text: str
    page: int | None = None
    score: float | None = None

