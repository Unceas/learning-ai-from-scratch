"""RAG Context Builder, Citation Mapping, and Source Attribution Service.

Transforms raw or normalized retrieval results into structured, LLM-ready context,
assigns deterministic citation markers ([S1], [S2]), constructs citation maps,
enforces context window chunk limits, handles zero-context fallbacks, and validates
generated citations against retrieved sources.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHUNKS = 8


class RetrievedChunk(BaseModel):
    """Normalized representation of a single retrieved document chunk."""
    text: str
    score: float = 0.0
    vector_score: Optional[float] = None
    reranker_score: Optional[float] = None
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
            vector_score=float(chunk["vector_score"]) if chunk.get("vector_score") is not None else None,
            reranker_score=float(chunk["reranker_score"]) if chunk.get("reranker_score") is not None else None,
            document_id=chunk.get("document_id"),
            filename=chunk.get("filename") or chunk.get("document") or "Unknown",
            chunk_index=chunk.get("chunk_index", chunk.get("chunk_id", chunk.get("chunk", 0))),
            page=chunk.get("page", 1),
            file_hash=chunk.get("file_hash")
        )
    return RetrievedChunk(text=str(chunk))


def build_context(chunks: List[RetrievedChunk]) -> str:
    """Format structured evidence sections for LLM ingestion with explicit [S1], [S2] source markers."""
    sections = []
    for i, chunk in enumerate(chunks, start=1):
        sections.append(
            f"""[S{i}]
File: {chunk.filename}
Chunk: {chunk.chunk_index}

{chunk.text}""".strip()
        )
    return "\n\n".join(sections)


def validate_citations(
    answer: str,
    sources_or_map: Union[List[Any], Dict[str, Any], int]
) -> Dict[str, Any]:
    """Extract and validate citation identifiers [S#] from an LLM response against actual retrieved sources.

    Args:
        answer: Model-generated text containing potential citations like [S1], [S2], [S99].
        sources_or_map: Retrieved source list, citation map dict, or integer source count.

    Returns:
        Dict containing:
            - valid_citations: list of valid citation tags (e.g. ['[S1]'])
            - invalid_citations: list of hallucinated citation tags (e.g. ['[S99]'])
            - is_valid: bool indicating if all generated citations are valid
    """
    valid_indices = set()
    if isinstance(sources_or_map, int):
        valid_indices = {str(i) for i in range(1, sources_or_map + 1)}
    elif isinstance(sources_or_map, dict):
        valid_indices = {str(k).lstrip("S") for k in sources_or_map.keys()}
    elif isinstance(sources_or_map, list):
        valid_indices = {str(i) for i in range(1, len(sources_or_map) + 1)}
        for item in sources_or_map:
            if isinstance(item, dict) and "id" in item:
                valid_indices.add(str(item["id"]).lstrip("S"))

    raw_ids = re.findall(r"\[S(\d+)\]", answer)
    unique_ids = []
    for sid in raw_ids:
        if sid not in unique_ids:
            unique_ids.append(sid)

    valid_citations = []
    invalid_citations = []

    for sid in unique_ids:
        tag = f"[S{sid}]"
        if sid in valid_indices:
            valid_citations.append(tag)
        else:
            invalid_citations.append(tag)

    if invalid_citations:
        logger.warning(
            "Generation quality problem: Invalid citation(s) detected in LLM response: %s",
            invalid_citations
        )

    return {
        "valid_citations": valid_citations,
        "invalid_citations": invalid_citations,
        "is_valid": len(invalid_citations) == 0
    }


def build_rag_context(
    chunks: List[Union[RetrievedChunk, Dict[str, Any]]],
    max_chunks: int = MAX_CONTEXT_CHUNKS
) -> Dict[str, Any]:
    """Transform retrieved chunks into structured context, citation map, and grouped document sources.

    Returns:
        Dict containing:
            - context: Formatted string of evidence with [S1], [S2] identifiers for LLM prompt.
            - sources: Detailed chunk-level source metadata with stable IDs.
            - citation_map: Deterministic mapping from 'S1', 'S2' to document/chunk metadata.
            - document_sources: Grouped document references containing chunk index lists.
            - has_context: Boolean indicating whether relevant context was found.
            - fallback_answer: Standardized explanation when no relevant context exists.
    """
    if not chunks:
        return {
            "context": "",
            "sources": [],
            "citation_map": {},
            "document_sources": [],
            "has_context": False,
            "fallback_answer": "I couldn't find enough information in the indexed documents."
        }

    normalized = [normalize_chunk(c) for c in chunks]
    limited_chunks = normalized[:max_chunks]

    context_str = build_context(limited_chunks)

    sources = []
    citation_map = {}
    for i, chunk in enumerate(limited_chunks, start=1):
        source_id = f"S{i}"
        source_dict = {
            "id": source_id,
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "chunk_index": chunk.chunk_index,
            "score": chunk.score,
            "vector_score": chunk.vector_score,
            "reranker_score": chunk.reranker_score,
            "page": chunk.page
        }
        sources.append(source_dict)
        citation_map[source_id] = {
            "id": source_id,
            "document_id": chunk.document_id,
            "filename": chunk.filename,
            "chunk_index": chunk.chunk_index,
            "score": chunk.score,
            "vector_score": chunk.vector_score,
            "reranker_score": chunk.reranker_score
        }

    # Group chunk indices by document for clean UI presentation
    grouped_docs = {}
    for chunk in limited_chunks:
        key = (chunk.document_id, chunk.filename)
        if key not in grouped_docs:
            grouped_docs[key] = []
        if chunk.chunk_index not in grouped_docs[key]:
            grouped_docs[key].append(chunk.chunk_index)

    document_sources = [
        {
            "document_id": doc_id,
            "filename": filename,
            "chunks": sorted(chunks_list)
        }
        for (doc_id, filename), chunks_list in grouped_docs.items()
    ]

    return {
        "context": context_str,
        "sources": sources,
        "citation_map": citation_map,
        "document_sources": document_sources,
        "has_context": True,
        "fallback_answer": None
    }
