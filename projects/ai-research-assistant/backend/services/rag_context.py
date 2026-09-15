"""RAG Context Builder and Source Attribution Service.

Transforms raw or normalized retrieval results into structured, LLM-ready context,
enforces context window chunk limits, handles zero-context fallbacks, and separates
independent source attribution metadata.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


MAX_CONTEXT_CHUNKS = 8


class RetrievedChunk(BaseModel):
    """Normalized representation of a single retrieved document chunk."""
    text: str
    score: float = 0.0
    document_id: Optional[int] = None
    filename: str = "Unknown"
    chunk_index: int = 0
    page: Optional[int] = 1
    file_hash: Optional[str] = None


def normalize_chunk(chunk: Union[RetrievedChunk, Dict[str, Any]]) -> RetrievedChunk:
    """Normalize a chunk dictionary or model instance into a standard RetrievedChunk."""
    if isinstance(chunk, RetrievedChunk):
        return chunk
    if isinstance(chunk, dict):
        return RetrievedChunk(
            text=chunk.get("text", ""),
            score=float(chunk.get("score", 0.0)),
            document_id=chunk.get("document_id"),
            filename=chunk.get("filename") or chunk.get("document") or "Unknown",
            chunk_index=chunk.get("chunk_index", chunk.get("chunk_id", chunk.get("chunk", 0))),
            page=chunk.get("page", 1),
            file_hash=chunk.get("file_hash")
        )
    return RetrievedChunk(text=str(chunk))


def build_context(chunks: List[RetrievedChunk]) -> str:
    """Format structured evidence sections for LLM ingestion with explicit source labels."""
    sections = []
    for i, chunk in enumerate(chunks, start=1):
        sections.append(
            f"""SOURCE {i}
File: {chunk.filename}
Document ID: {chunk.document_id}
Chunk: {chunk.chunk_index}

{chunk.text}""".strip()
        )
    return "\n\n".join(sections)


def build_rag_context(
    chunks: List[Union[RetrievedChunk, Dict[str, Any]]],
    max_chunks: int = MAX_CONTEXT_CHUNKS
) -> Dict[str, Any]:
    """Transform retrieved chunks into structured context, chunk-level sources, and deduplicated doc sources.
    
    Returns:
        Dict containing:
            - context: Formatted string of evidence for LLM prompt.
            - sources: Detailed chunk-level source metadata for API responses.
            - document_sources: Deduplicated document-level references.
            - has_context: Boolean indicating whether relevant context was found.
            - fallback_answer: Standardized explanation when no relevant context exists.
    """
    if not chunks:
        return {
            "context": "",
            "sources": [],
            "document_sources": [],
            "has_context": False,
            "fallback_answer": "I couldn't find relevant information in the indexed documents."
        }

    normalized = [normalize_chunk(c) for c in chunks]
    limited_chunks = normalized[:max_chunks]

    context_str = build_context(limited_chunks)

    sources = [
        {
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "chunk_index": chunk.chunk_index,
            "page": chunk.page,
            "score": chunk.score
        }
        for chunk in limited_chunks
    ]

    seen_docs = set()
    document_sources = []
    for chunk in limited_chunks:
        doc_key = (chunk.document_id, chunk.filename)
        if doc_key not in seen_docs:
            seen_docs.add(doc_key)
            document_sources.append({
                "document_id": chunk.document_id,
                "filename": chunk.filename
            })

    return {
        "context": context_str,
        "sources": sources,
        "document_sources": document_sources,
        "has_context": True,
        "fallback_answer": None
    }
