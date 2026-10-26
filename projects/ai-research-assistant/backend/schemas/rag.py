"""Pydantic schemas for RAG requests, responses, and citations."""

from typing import Any

from pydantic import BaseModel, Field


class Source(BaseModel):
    """Structured citation source metadata for a retrieved chunk."""
    id: str = "S1"
    document_id: int
    filename: str
    chunk_index: int
    score: float = 0.0
    text: str = ""
    page: int | None = None
    vector_score: float | None = None
    reranker_score: float | None = None
    matched_queries: list[str] | None = Field(default_factory=list)


class DocumentGroupedSource(BaseModel):
    """Document-level source grouping chunk indices for clean frontend display."""
    document_id: int
    filename: str
    chunks: list[int] = Field(default_factory=list)


class QueryInfo(BaseModel):
    original: str
    rewritten: str | None = None


class RAGResponse(BaseModel):
    """Structured response contract for RAG answer generation and citation attribution."""
    answer: str
    sources: list[Source] = Field(default_factory=list)
    citation_map: dict[str, Source] | None = None
    invalid_citations: list[str] | None = Field(default_factory=list)
    document_sources: list[DocumentGroupedSource] | None = None
    subqueries: list[str] | None = Field(default_factory=list)
    expanded_queries: list[str] | None = Field(default_factory=list)
    used_hyde: bool | None = False
    query: Any | None = None
    conversation_id: int | None = None
