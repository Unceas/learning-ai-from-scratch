"""RAG Service encapsulating retrieval, ranking, and answer generation logic."""

from typing import Dict, Any, Optional
import vector_store
from tool_router import execute_tool
from llm import generate_answer
from observability import RAGTrace, timed_call, save_trace


def run_rag_pipeline(query: str, filename: Optional[str] = None, user_id: str = "default_user") -> Dict[str, Any]:
    """Execute the full RAG pipeline and return structured result payload."""
    trace = RAGTrace(query=query)

    trace.tool_calls.append({
        "tool": "document_search",
        "arguments": {"query": query, "filename": filename, "user_id": user_id}
    })

    results, search_time = timed_call(
        execute_tool,
        "document_search",
        {"query": query, "filename": filename, "user_id": user_id}
    )

    trace.retrieval_ms = search_time
    trace.retrieved_count = 20
    trace.final_context_count = len(results)

    # Collect streaming tokens into complete answer
    stream = generate_answer(query, results, user_id=user_id)
    answer_chunks = []
    for chunk in stream:
        answer_chunks.append(chunk)

    full_answer = "".join(answer_chunks)
    trace.sources = [
        {
            "document": r.get("document"),
            "page": r.get("page"),
            "chunk": r.get("chunk")
        }
        for r in results
    ]

    save_trace(trace)

    return {
        "query": query,
        "answer": full_answer,
        "sources": results,
        "latency_ms": search_time
    }
