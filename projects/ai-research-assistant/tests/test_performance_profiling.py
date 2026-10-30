"""Unit and integration tests for Day 173: Performance Profiling and Latency Optimization."""

import asyncio
import os
import sys
import time
from typing import Any


# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.embedding_service import EmbeddingService
from backend.services.keyword_retriever import (
    KeywordRetriever,
    KeywordRetrieverCache,
    bm25_cache,
    get_or_build_keyword_retriever,
)
from backend.services.observability import (
    PerformanceTracker,
    async_measure_stage,
    benchmark,
    measure_stage,
    performance_tracker,
)
from backend.services.rag_context import (
    RetrievedChunk,
    build_rag_context,
    deduplicate_near_identical_chunks,
)
from backend.services.rag_service import run_rag_pipeline


# ============================================================================
# 1. Stage-Level Timing & Observability (Section 2)
# ============================================================================

def test_measure_stage_single_arg():
    """measure_stage works as a simple context manager with just a stage name."""
    performance_tracker.clear()
    with measure_stage("retrieval"):
        time.sleep(0.002)

    stats = performance_tracker.get_percentiles("retrieval")
    assert stats["count"] == 1
    assert stats["p50_ms"] >= 1.0


def test_measure_stage_with_metrics_dict():
    """measure_stage populates dictionary for backward compatibility with previous days."""
    metrics: dict[str, Any] = {}
    with measure_stage("reranking", metrics):
        time.sleep(0.002)

    assert "reranking" in metrics
    assert metrics["reranking"] >= 1.0


def test_async_measure_stage():
    """async_measure_stage correctly tracks asynchronous coroutine execution time."""
    async def scenario():
        performance_tracker.clear()
        metrics: dict[str, Any] = {}
        async with async_measure_stage("async_llm_generation", metrics):
            await asyncio.sleep(0.005)

        assert "async_llm_generation" in metrics
        assert metrics["async_llm_generation"] >= 4.0
        stats = performance_tracker.get_percentiles("async_llm_generation")
        assert stats["count"] == 1

    asyncio.run(scenario())


def test_performance_tracker_percentiles():
    """PerformanceTracker calculates accurate percentiles and summary statistics."""
    tracker = PerformanceTracker(max_samples=100)
    # Record 100 sample latencies from 1.0ms to 100.0ms
    for i in range(1, 101):
        tracker.record("test_stage", float(i))

    stats = tracker.get_percentiles("test_stage")
    assert stats["count"] == 100
    assert stats["min_ms"] == 1.0
    assert stats["max_ms"] == 100.0
    assert stats["p50_ms"] == 51.0  # Median
    assert stats["p90_ms"] == 91.0
    assert stats["p95_ms"] == 96.0
    assert stats["p99_ms"] == 100.0
    assert stats["outcomes"]["success"] == 100


def test_performance_tracker_empty_stage():
    """PerformanceTracker gracefully handles unrecorded stages without crashing."""
    tracker = PerformanceTracker()
    stats = tracker.get_percentiles("non_existent_stage")
    assert stats["count"] == 0
    assert stats["p50_ms"] == 0.0
    assert stats["mean_ms"] == 0.0


# ============================================================================
# 2. Benchmark Harness (Section 7)
# ============================================================================

def test_benchmark_function():
    """benchmark() calculates iterations, mean, median, P50, and P95."""
    call_count = 0

    def task():
        nonlocal call_count
        call_count += 1
        time.sleep(0.001)

    result = benchmark(task, iterations=10)
    assert result["iterations"] == 10
    assert call_count == 10
    assert "mean_ms" in result
    assert "median_ms" in result
    assert "p50_ms" in result
    assert "p95_ms" in result
    assert result["p95_ms"] >= result["p50_ms"]


# ============================================================================
# 3. Document Ingestion & Embedding Batching (Section 3)
# ============================================================================

def test_embedding_service_batch_size():
    """EmbeddingService processes texts in configurable batches without exceeding limit."""
    embedder = EmbeddingService()
    test_texts = [f"Text chunk number {i} for batch test" for i in range(10)]

    # Test embed_documents
    results = embedder.embed_documents(test_texts, user_id="test_user_batch")
    assert len(results) == 10
    assert all(isinstance(v, list) and len(v) > 0 for v in results)


def test_embedding_service_empty_input():
    """EmbeddingService handles empty input cleanly."""
    embedder = EmbeddingService()
    assert embedder.embed_documents([]) == []
    assert embedder.embed_query("") == []


# ============================================================================
# 4. BM25 Caching & Invalidation (Section 4)
# ============================================================================

def test_bm25_cache_hit_and_miss():
    """KeywordRetrieverCache records cache misses on first fetch and hits on subsequent fetches."""
    cache = KeywordRetrieverCache(max_entries=5)
    chunks = [{"text": "Machine learning architectures and deep neural networks", "document_id": 1, "chunk_index": 0}]

    user_id = "user_bm25_test"
    sig = cache.compute_signature([1], len(chunks))

    # Initial lookup is a miss
    assert cache.get(user_id, sig) is None
    assert cache.misses == 1

    # Populate cache
    retriever = KeywordRetriever(chunks)
    cache.put(user_id, sig, retriever)

    # Second lookup is a hit
    cached_retriever = cache.get(user_id, sig)
    assert cached_retriever is retriever
    assert cache.hits == 1


def test_bm25_cache_user_invalidation():
    """KeywordRetrieverCache invalidates only the target user's entries."""
    cache = KeywordRetrieverCache(max_entries=5)
    retriever = KeywordRetriever([{"text": "Sample text"}])

    cache.put("user_a", "sig_a", retriever)
    cache.put("user_b", "sig_b", retriever)

    assert cache.get("user_a", "sig_a") is not None
    assert cache.get("user_b", "sig_b") is not None

    # Invalidate user_a
    cache.invalidate_user("user_a")
    assert cache.get("user_a", "sig_a") is None
    assert cache.get("user_b", "sig_b") is not None


def test_get_or_build_keyword_retriever_reuses_cached():
    """get_or_build_keyword_retriever returns cached instance without rebuilding."""
    bm25_cache.clear()
    chunks = [
        {"document_id": 10, "chunk_index": 0, "text": "Dense retrieval versus sparse lexical retrieval."},
        {"document_id": 10, "chunk_index": 1, "text": "Reciprocal rank fusion combines scores efficiently."},
    ]

    r1 = get_or_build_keyword_retriever("user_x", chunks, document_ids=[10])
    r2 = get_or_build_keyword_retriever("user_x", chunks, document_ids=[10])

    assert r1 is r2
    assert bm25_cache.stats()["hits"] == 1


# ============================================================================
# 5. Context Chunk Deduplication & Optimization (Section 5)
# ============================================================================

def test_deduplicate_near_identical_chunks():
    """deduplicate_near_identical_chunks prunes high-overlap chunks while preserving diversity."""
    chunks = [
        RetrievedChunk(text="Vector search systems scale horizontally using inverted file indexes.", score=0.9),
        RetrievedChunk(text="Vector search systems scale horizontally using inverted file indexes.", score=0.88),  # Duplicate
        RetrievedChunk(text="Quantization methods reduce memory footprint of dense embeddings.", score=0.85),
    ]

    deduped = deduplicate_near_identical_chunks(chunks, min_jaccard_similarity=0.85)
    assert len(deduped) == 2
    assert deduped[0].text.startswith("Vector search")
    assert deduped[1].text.startswith("Quantization")


def test_build_rag_context_with_deduplication():
    """build_rag_context enables deduplication by default and limits context chunks."""
    duplicate_chunks = [
        {"text": "Transformers employ multi-head self-attention mechanisms.", "document_id": 1, "chunk_index": 0},
        {"text": "Transformers employ multi-head self-attention mechanisms.", "document_id": 1, "chunk_index": 1},
        {"text": "Feed-forward layers process attention outputs independently.", "document_id": 1, "chunk_index": 2},
    ]

    payload = build_rag_context(duplicate_chunks, deduplicate=True)
    assert len(payload["sources"]) == 2  # One duplicate eliminated
    assert payload["has_context"] is True
    assert "[S1]" in payload["context"]
    assert "[S2]" in payload["context"]


# ============================================================================
# 6. Complete Pipeline Stage Instrumentation (T1 - T7)
# ============================================================================

from unittest.mock import patch

@patch("backend.services.rag_service.generate_answer")
@patch("backend.services.rag_service.db_retrieve")
def test_pipeline_t1_through_t7_instrumentation(mock_retrieve, mock_generate):
    """Verify that run_rag_pipeline records stage timings T1 through T7."""
    mock_retrieve.return_value = [
        {
            "text": "Quantum superposition principles and wavefunctions.",
            "score": 0.95,
            "filename": "quantum.pdf",
            "chunk_index": 0,
        }
    ]
    mock_generate.return_value = [
        "Quantum superposition allows qubits to represent linear combinations [S1]."
    ]

    metrics: dict[str, Any] = {}
    res = run_rag_pipeline(
        query="What is quantum superposition?",
        user_id="test_perf_pipeline_user",
        metrics=metrics,
    )

    # Verify T1: request_validation
    assert "request_validation" in metrics
    assert isinstance(metrics["request_validation"], (int, float))

    # Verify T2: query_routing
    assert "query_routing" in metrics

    # Verify T3: retrieval
    assert "retrieval" in metrics

    # Verify T4: reranking
    assert "reranking" in metrics

    # Verify T5: context_assembly
    assert "context_assembly" in metrics

    # Verify T6: generation
    assert "generation" in metrics

    # Verify T7: response_validation
    assert "response_validation" in metrics

    # Verify response structure intact
    assert "answer" in res
    assert "metrics" in res
    assert res["metrics"] is metrics
