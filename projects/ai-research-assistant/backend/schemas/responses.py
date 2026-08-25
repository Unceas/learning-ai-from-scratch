"""Pydantic schemas for API response validation and documentation contracts."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    detail: str


class DocumentResponse(BaseModel):
    status: str
    filename: Optional[str] = None
    pages: Optional[int] = None
    chunks: Optional[int] = None


class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
