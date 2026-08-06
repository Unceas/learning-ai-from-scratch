"""Observability module for RAG pipeline performance tracing and logging."""

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple


@dataclass
class RAGTrace:
    """Data structure representing telemetry metrics for a single RAG request."""

    query: str

    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0
    ttft_ms: float = 0.0

    retrieved_count: int = 0
    final_context_count: int = 0
    streamed: bool = True
    tokens_generated: int = 0

    sources: List[Dict[str, Any]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    reflection: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_ms(self) -> float:
        """Calculate total latency across retrieval, re-ranking, and generation."""
        return (
            self.retrieval_ms
            + self.reranking_ms
            + self.generation_ms
        )


def timed_call(function: Callable[..., Any], *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """Execute a function and measure its elapsed execution latency in milliseconds.

    Args:
        function: Target function to execute.
        *args: Positional arguments.
        **kwargs: Keyword arguments.

    Returns:
        Tuple of (function_result, latency_in_ms).
    """
    start = time.perf_counter()

    result = function(*args, **kwargs)

    elapsed_ms = (time.perf_counter() - start) * 1000.0

    return result, elapsed_ms


def save_trace(trace: RAGTrace, path: str = "rag_traces.jsonl") -> None:
    """Persist a structured RAG trace record to a JSON Lines log file.

    Args:
        trace: RAGTrace instance containing request telemetry.
        path: Path to the output JSONL file.
    """
    record = {
        "query": trace.query,
        "retrieval_ms": round(trace.retrieval_ms, 2),
        "reranking_ms": round(trace.reranking_ms, 2),
        "generation_ms": round(trace.generation_ms, 2),
        "ttft_ms": round(trace.ttft_ms, 2),
        "total_ms": round(trace.total_ms, 2),
        "retrieved_count": trace.retrieved_count,
        "final_context_count": trace.final_context_count,
        "streamed": trace.streamed,
        "tokens_generated": trace.tokens_generated,
        "sources": trace.sources,
        "tool_calls": trace.tool_calls,
        "steps": trace.steps,
        "reflection": trace.reflection
    }

    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")
