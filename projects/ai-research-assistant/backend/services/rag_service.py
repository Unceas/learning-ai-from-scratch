"""RAG Service encapsulating retrieval, ranking, context construction, and answer generation logic."""

import time
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from tool_router import execute_tool
from llm import generate_answer
from observability import RAGTrace, timed_call, save_trace
from backend.services.rag_context import build_rag_context, validate_citations
from backend.database import SessionLocal
from backend.config import settings
from backend.services.reranker import get_reranker
from retrieval import db_retrieve


def run_rag_pipeline(
    query: str,
    filename: Optional[str] = None,
    user_id: str = "default_user",
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Execute the full RAG pipeline with candidate retrieval, reranking, context building, and citations."""
    trace = RAGTrace(query=query)
    start_time = time.time()

    # 1. First stage: Retrieve candidate chunks (prioritize recall) strictly scoped to user's indexed docs
    results = []
    close_db = False
    session = db
    if session is None:
        try:
            session = SessionLocal()
            close_db = True
        except Exception:
            session = None

    candidate_k = getattr(settings, "rag_candidate_k", 20)
    final_k = getattr(settings, "rag_final_k", 5)

    if session is not None:
        try:
            results = db_retrieve(db=session, user_id=user_id, query=query, top_k=candidate_k)
        except Exception:
            results = []
        finally:
            if close_db and session is not None:
                session.close()

    # Fallback to tool router document search for unindexed or legacy mocks
    if not results:
        try:
            trace.tool_calls.append({
                "tool": "document_search",
                "arguments": {"query": query, "filename": filename, "user_id": user_id}
            })
            tool_results = execute_tool(
                "document_search",
                {"query": query, "filename": filename, "user_id": user_id}
            )
            if isinstance(tool_results, list) and len(tool_results) > 0:
                if not (isinstance(tool_results[0], dict) and "error" in tool_results[0]):
                    results = tool_results
        except Exception:
            pass

    search_time = round((time.time() - start_time) * 1000, 2)
    trace.retrieval_ms = search_time
    trace.retrieved_count = len(results)

    # 2. Second stage: Cross-encoder reranking (prioritize precision)
    rerank_start = time.time()
    if results and getattr(settings, "reranker_enabled", True):
        reranker = get_reranker()
        results = reranker.rerank(query=query, chunks=results, top_k=final_k)
    else:
        results = results[:final_k]
    trace.reranking_ms = round((time.time() - rerank_start) * 1000, 2)

    # 3. Build structured RAG context, citation map, and independent source attribution
    rag_payload = build_rag_context(results)
    trace.final_context_count = len(rag_payload["sources"])

    # 4. Clean early exit for zero-chunk retrieval (prevents LLM hallucination and saves tokens)
    if not rag_payload["has_context"]:
        save_trace(trace)
        return {
            "query": query,
            "answer": rag_payload["fallback_answer"],
            "sources": [],
            "citation_map": {},
            "invalid_citations": [],
            "document_sources": [],
            "has_context": False,
            "latency_ms": search_time
        }

    # 4. Stream response using Gemini LLM with grounded evidence context
    stream = generate_answer(query=query, context=rag_payload["context"], user_id=user_id)
    answer_chunks = []
    for chunk in stream:
        answer_chunks.append(chunk)

    full_answer = "".join(answer_chunks)
    validation = validate_citations(full_answer, rag_payload["citation_map"])
    trace.sources = rag_payload["sources"]
    save_trace(trace)

    return {
        "query": query,
        "answer": full_answer,
        "context": rag_payload["context"],
        "sources": rag_payload["sources"],
        "citation_map": rag_payload["citation_map"],
        "invalid_citations": validation["invalid_citations"],
        "document_sources": rag_payload["document_sources"],
        "has_context": True,
        "latency_ms": search_time
    }
