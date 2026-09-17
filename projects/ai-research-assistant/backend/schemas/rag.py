"""Pydantic schemas for RAG requests, responses, and citations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Source(BaseModel):
    """Structured citation source metadata for a retrieved chunk."""
    id: str = "S1"
    document_id: int
    filename: str
    chunk_index: int
    score: float = 0.0


class DocumentGroupedSource(BaseModel):
    """Document-level source grouping chunk indices for clean frontend display."""
    document_id: int
    filename: str
    chunks: List[int] = Field(default_factory=list)


class RAGResponse(BaseModel):
    """Structured response contract for RAG answer generation and citation attribution."""
    answer: str
    sources: List[Source] = Field(default_factory=list)
    citation_map: Optional[Dict[str, Source]] = None
    invalid_citations: Optional[List[str]] = Field(default_factory=list)
    document_sources: Optional[List[DocumentGroupedSource]] = None
