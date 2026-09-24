"""RAG Service encapsulating retrieval, ranking, context construction, and answer generation logic."""

import logging
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
from backend.services.query_router import classify_query, get_retrieval_config, QueryType
from backend.services.query_decomposer import decompose_query
from backend.services.keyword_retriever import KeywordRetriever
from backend.services.rank_fusion import reciprocal_rank_fusion
from backend.services.document_db_service import get_indexed_document_ids
from backend.services.vector_store import VectorStore
from retrieval import db_retrieve

logger = logging.getLogger(__name__)


def run_rag_pipeline(
    query: str,
    filename: Optional[str] = None,
    user_id: str = "default_user",
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """Execute the full RAG pipeline with candidate retrieval, reranking, context building, and citations."""
    # 0. Query Routing: Classify query archetype and resolve retrieval configuration
    if getattr(settings, "query_routing_enabled", True):
        query_type = classify_query(query)
        routing_cfg = get_retrieval_config(query_type)
        candidate_k = routing_cfg["candidate_k"]
        final_k = routing_cfg["final_k"]
    else:
        query_type = QueryType.SEMANTIC
        candidate_k = getattr(settings, "rag_candidate_k", 20)
        final_k = getattr(settings, "rag_final_k", 5)

    # 1. Multi-Query Decomposition:
    # Decompose complex comparison queries into focused search subqueries
    multi_query_active = (
        getattr(settings, "multi_query_enabled", True)
        and query_type == QueryType.COMPARISON
    )
    if multi_query_active:
        subqueries = decompose_query(query)
        if not subqueries:
            subqueries = [query]
    else:
        subqueries = [query]

    # Enforce maximum subqueries limit
    max_subs = getattr(settings, "max_subqueries", 4)
    subqueries = subqueries[:max_subs]

    trace = RAGTrace(
        query=query,
        query_type=query_type.value,
        candidate_k=candidate_k,
        final_k=final_k,
        subqueries=subqueries
    )
    logger.info(
        "Query routing: query='%s', type=%s, candidate_k=%d, final_k=%d, subqueries=%s",
        query, query_type.value, candidate_k, final_k, subqueries
    )
    start_time = time.time()

    # 2. First stage: Retrieve candidate chunks across subqueries strictly scoped to user's indexed docs
    session = db
    close_db = False
    if session is None:
        try:
            session = SessionLocal()
            close_db = True
        except Exception:
            session = None

    # Initialize BM25 KeywordRetriever once across eligible indexed documents
    keyword_retriever = None
    if session is not None and getattr(settings, "hybrid_retrieval_enabled", True) and getattr(settings, "bm25_enabled", True):
        try:
            indexed_doc_ids = get_indexed_document_ids(session, user_id)
            if indexed_doc_ids:
                vector_store = VectorStore()
                user_chunks = vector_store.get_user_chunks(user_id=user_id, document_ids=indexed_doc_ids)
                if user_chunks:
                    keyword_retriever = KeywordRetriever(user_chunks)
        except Exception as e:
            logger.debug("Failed initializing KeywordRetriever: %s", e)
            keyword_retriever = None

    deduped_candidates: Dict[Any, Dict[str, Any]] = {}

    try:
        for sq in subqueries:
            dense_results = []
            if session is not None:
                try:
                    dense_results = db_retrieve(db=session, user_id=user_id, query=sq, top_k=candidate_k)
                except Exception:
                    dense_results = []

            # Retrieve BM25 keyword candidates if hybrid retrieval is active
            keyword_results = []
            if keyword_retriever is not None:
                try:
                    keyword_results = keyword_retriever.retrieve(query=sq, top_k=candidate_k)
                except Exception:
                    keyword_results = []

            # Fuse dense and keyword results with Reciprocal Rank Fusion
            if keyword_results and dense_results:
                rrf_k = getattr(settings, "rrf_k", 60)
                fused = reciprocal_rank_fusion([dense_results, keyword_results], k=rrf_k)
                sq_results = [item["chunk"] for item in fused[:candidate_k]]
            elif keyword_results:
                sq_results = [item["chunk"] for item in keyword_results[:candidate_k]]
            else:
                sq_results = dense_results

            # Fallback to tool router document search for unindexed or legacy mocks
            if not sq_results:
                try:
                    trace.tool_calls.append({
                        "tool": "document_search",
                        "arguments": {"query": sq, "filename": filename, "user_id": user_id}
                    })
                    tool_results = execute_tool(
                        "document_search",
                        {"query": sq, "filename": filename, "user_id": user_id}
                    )
                    if isinstance(tool_results, list) and len(tool_results) > 0:
                        if not (isinstance(tool_results[0], dict) and "error" in tool_results[0]):
                            sq_results = tool_results
                except Exception:
                    pass

            for chunk in sq_results:
                # Key chunk by (document_id, chunk_index) or fallback identifiers
                doc_id = chunk.get("document_id")
                c_idx = chunk.get("chunk_index", chunk.get("chunk_id", chunk.get("chunk", 0)))
                if doc_id is not None:
                    chunk_key = (doc_id, c_idx)
                elif chunk.get("filename"):
                    chunk_key = (chunk.get("filename"), c_idx)
                else:
                    chunk_key = chunk.get("id") or chunk.get("text", "")[:100]

                if chunk_key not in deduped_candidates:
                    chunk_copy = dict(chunk)
                    chunk_copy["matched_queries"] = [sq]
                    deduped_candidates[chunk_key] = chunk_copy
                else:
                    existing = deduped_candidates[chunk_key]
                    if "matched_queries" not in existing:
                        existing["matched_queries"] = []
                    if sq not in existing["matched_queries"]:
                        existing["matched_queries"].append(sq)
                    current_score = float(chunk.get("score", 0.0))
                    existing_score = float(existing.get("score", 0.0))
                    if current_score > existing_score:
                        existing["score"] = current_score
                        existing["vector_score"] = float(chunk.get("vector_score", current_score))
    finally:
        if close_db and session is not None:
            session.close()

    results = list(deduped_candidates.values())

    search_time = round((time.time() - start_time) * 1000, 2)
    trace.retrieval_ms = search_time
    trace.retrieved_count = len(results)

    # 3. Second stage: Cross-encoder reranking against ORIGINAL query (prioritize precision)
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
            "query_type": query_type.value,
            "subqueries": subqueries,
            "routing": {
                "query_type": query_type.value,
                "candidate_k": candidate_k,
                "final_k": final_k,
                "subqueries": subqueries
            },
            "answer": rag_payload["fallback_answer"],
            "sources": [],
            "citation_map": {},
            "invalid_citations": [],
            "document_sources": [],
            "has_context": False,
            "latency_ms": search_time + trace.reranking_ms
        }

    # 5. Stream response using Gemini LLM with grounded evidence context
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
        "query_type": query_type.value,
        "subqueries": subqueries,
        "routing": {
            "query_type": query_type.value,
            "candidate_k": candidate_k,
            "final_k": final_k,
            "subqueries": subqueries
        },
        "answer": full_answer,
        "context": rag_payload["context"],
        "sources": rag_payload["sources"],
        "citation_map": rag_payload["citation_map"],
        "invalid_citations": validation["invalid_citations"],
        "document_sources": rag_payload["document_sources"],
        "has_context": True,
        "latency_ms": search_time + trace.reranking_ms
    }
