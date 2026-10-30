"""Performance benchmarking and latency profiling harness for AI Research Assistant pipeline stages."""

import os
import sys
import time
from typing import Any


# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.chunker import chunk_text
from backend.services.keyword_retriever import (
    KeywordRetriever,
    bm25_cache,
    get_or_build_keyword_retriever,
)
from backend.services.observability import (
    benchmark,
    measure_stage,
    performance_tracker,
)
from backend.services.rag_context import (
    build_rag_context,
)


# ============================================================================
# 1. Benchmark Harness Core Verification
# ============================================================================

def test_benchmark_harness_statistics():
    """Verify that benchmark() correctly calculates mean, median, P50, and P95 metrics."""
    counter = 0

    def work():
        nonlocal counter
        counter += 1
        time.sleep(0.001)  # 1ms work

    results = benchmark(work, iterations=15)
    assert results["iterations"] == 15
    assert counter == 15
    assert "mean_ms" in results
    assert "median_ms" in results
    assert "p50_ms" in results
    assert "p95_ms" in results
    assert results["mean_ms"] >= 0.5
    assert results["p95_ms"] >= results["p50_ms"]


# ============================================================================
# 2. Document Processing & Chunking Microbenchmark
# ============================================================================

def test_document_chunking_benchmark():
    """Benchmark text chunking latency across varying text sizes."""
    sample_text = (
        "Quantum computing utilizes quantum mechanical phenomena such as superposition and entanglement. "
        "Unlike classical bits which represent 0 or 1, qubits represent complex linear combinations. "
        "Error correction in surface codes requires physical-to-logical qubit ratios above 1000:1. "
    ) * 50  # ~150 sentences

    res = benchmark(lambda: chunk_text(sample_text), iterations=25)
    assert res["mean_ms"] < 50.0  # Fast in-memory chunking
    assert res["p95_ms"] < 100.0


# ============================================================================
# 3. BM25 Caching vs Rebuild Microbenchmark
# ============================================================================

def test_bm25_retrieval_caching_benchmark():
    """Demonstrate that cached BM25 keyword retriever outperforms un-cached re-indexing on every query."""
    user_id = "bench_user_bm25"
    chunks = [
        {"document_id": 1, "chunk_index": i, "text": f"Technical specification section {i} describing distributed vector databases and indexing strategies."}
        for i in range(40)
    ]

    # Clear cache before starting
    bm25_cache.clear()

    # 1. Benchmark uncached: re-creating retriever every query
    uncached_stats = benchmark(
        lambda: KeywordRetriever(chunks).retrieve("distributed vector databases", top_k=5),
        iterations=20
    )

    # 2. Benchmark cached: reusing retriever via get_or_build_keyword_retriever
    cached_stats = benchmark(
        lambda: get_or_build_keyword_retriever(user_id=user_id, chunks=chunks, document_ids=[1]).retrieve("distributed vector databases", top_k=5),
        iterations=20
    )

    # Cached retrieval should be substantially faster than rebuilding index each time
    assert cached_stats["mean_ms"] <= uncached_stats["mean_ms"]
    assert bm25_cache.stats()["hits"] >= 19


# ============================================================================
# 4. Context Optimization & Near-Duplicate Pruning Microbenchmark
# ============================================================================

def test_context_deduplication_benchmark():
    """Verify context deduplication prunes near-identical chunks and saves prompt characters."""
    repeated_chunks = [
        {"document_id": 1, "chunk_index": 0, "text": "Superconducting qubits require dilution refrigerators operating at 15 millikelvin temperatures.", "score": 0.95},
        {"document_id": 1, "chunk_index": 1, "text": "Superconducting qubits require dilution refrigerators operating at 15 millikelvin temperatures.", "score": 0.94},  # exact dupe
        {"document_id": 1, "chunk_index": 2, "text": "Superconducting qubits require dilution refrigerators operating at 15 mK temperatures.", "score": 0.90},  # near dupe
        {"document_id": 2, "chunk_index": 0, "text": "Neutral atom quantum computers trap rubidium atoms in optical tweezer arrays.", "score": 0.88},
        {"document_id": 2, "chunk_index": 1, "text": "Trapped ion architectures employ laser cooling and RF Paul traps for fidelity.", "score": 0.85},
    ]

    # Without deduplication
    ctx_raw = build_rag_context(repeated_chunks, deduplicate=False)
    # With deduplication
    ctx_dedup = build_rag_context(repeated_chunks, deduplicate=True)

    assert len(ctx_dedup["sources"]) < len(ctx_raw["sources"])
    assert len(ctx_dedup["context"]) < len(ctx_raw["context"])
    assert ctx_dedup["has_context"] is True


# ============================================================================
# 5. Full Stage-Level Pipeline Timing & Observability
# ============================================================================

def test_stage_level_timing_instrumentation():
    """Verify that all pipeline stages T1-T7 record duration and update performance_tracker."""
    performance_tracker.clear()
    metrics: dict[str, Any] = {}

    with measure_stage("request_validation", metrics):
        time.sleep(0.002)

    with measure_stage("query_rewriting", metrics):
        time.sleep(0.003)

    with measure_stage("retrieval", metrics):
        time.sleep(0.005)

    with measure_stage("reranking", metrics):
        time.sleep(0.004)

    with measure_stage("context_assembly", metrics):
        time.sleep(0.002)

    with measure_stage("generation", metrics):
        time.sleep(0.006)

    with measure_stage("response_validation", metrics):
        time.sleep(0.002)

    # Check metrics dict populated
    assert "request_validation" in metrics
    assert "query_rewriting" in metrics
    assert "retrieval" in metrics
    assert "reranking" in metrics
    assert "context_assembly" in metrics
    assert "generation" in metrics
    assert "response_validation" in metrics

    # Check performance tracker percentiles
    all_stats = performance_tracker.get_all_stats()
    assert "retrieval" in all_stats
    ret_stats = all_stats["retrieval"]
    assert ret_stats["count"] == 1
    assert ret_stats["p50_ms"] >= 3.0
    assert ret_stats["p95_ms"] >= 3.0
