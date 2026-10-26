"""Benchmark comparing candidate retrieval performance with and without bounded LRU caching."""

import json
import os
import sys
import time
from collections.abc import Callable
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.evaluation.latency_report import summarize_latency
from backend.services.retrieval_cache import RetrievalCache


def run_retrieval_benchmark(
    retrieve_fn: Callable[[str], list[dict[str, Any]]] | None = None,
    queries: list[str] | None = None,
    user_id: str = "benchmark_researcher",
    eligible_docs: list[dict[str, Any]] | None = None,
    retrieval_config: dict[str, Any] | None = None,
    trials: int = 5,
    max_entries: int = 128,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Execute comparative benchmark between cache-disabled and cache-enabled retrieval.

    Args:
        retrieve_fn: Function simulating or executing candidate retrieval.
                     Defaults to realistic retrieval simulation with vector search overhead.
        queries: List of query texts to retrieve candidates for.
        user_id: Authenticated user ID for authorization scoping.
        eligible_docs: List of authorized indexed document records with index_version.
        retrieval_config: Retrieval parameters (strategy, top_k, candidate count).
        trials: Number of trials for statistical stability.
        max_entries: Cache size.
        output_path: Optional JSON output path.

    Returns:
        Structured benchmark report with latencies, speedups, and cache statistics.
    """
    if retrieve_fn is None:
        def simulated_retrieve(query_text: str) -> list[dict[str, Any]]:
            # Simulate embedding lookup + ChromaDB vector search + SQLite doc join
            time.sleep(0.005)  # 5ms simulated retrieval latency
            return [
                {
                    "text": f"Candidate passage for {query_text[:20]}",
                    "score": 0.88,
                    "document_id": 1,
                    "chunk_index": i,
                }
                for i in range(5)
            ]
        retrieve_fn = simulated_retrieve

    if eligible_docs is None:
        eligible_docs = [
            {"id": 1, "index_version": 1},
            {"id": 2, "index_version": 1},
        ]

    if retrieval_config is None:
        retrieval_config = {"strategy": "dense", "top_k": 5}

    if queries is None:
        # Representative corpus of queries with realistic repetition (60% repeated)
        base_queries = [
            "What is multi-head self-attention in Transformer models?",
            "How does FlashAttention optimize GPU memory bandwidth?",
            "Explain parameter-efficient fine-tuning with LoRA.",
            "Compare BERT encoder pre-training to GPT autoregressive decoder.",
            "What is Reciprocal Rank Fusion for hybrid retrieval?",
        ]
        # 25 total requests using 5 distinct queries
        queries = base_queries * 5

    # 1. Warm-up
    for q in queries[:2]:
        retrieve_fn(q)

    # 2. Run Cache Disabled Workload
    disabled_call_count = 0

    def run_disabled_trial() -> float:
        nonlocal disabled_call_count
        start = time.perf_counter()
        for q in queries:
            retrieve_fn(q)
            disabled_call_count += 1
        return (time.perf_counter() - start) * 1000

    disabled_trial_times = [run_disabled_trial() for _ in range(trials)]

    # 3. Run Cache Enabled Workload
    cache = RetrievalCache(max_entries=max_entries)
    enabled_compute_count = 0

    def run_enabled_trial() -> float:
        nonlocal enabled_compute_count
        start = time.perf_counter()
        for q in queries:
            key = cache.make_key(
                user_id=user_id,
                eligible_documents=eligible_docs,
                query=q,
                retrieval_config=retrieval_config,
            )
            cached = cache.get(key)
            if cached is None:
                candidates = retrieve_fn(q)
                enabled_compute_count += 1
                cache.set(key, candidates)
        return (time.perf_counter() - start) * 1000

    enabled_trial_times = [run_enabled_trial() for _ in range(trials)]

    disabled_summary = summarize_latency(disabled_trial_times)
    enabled_summary = summarize_latency(enabled_trial_times)
    stats = cache.stats()

    speedup = 1.0
    if enabled_summary["mean_ms"] and enabled_summary["mean_ms"] > 0:
        speedup = round(disabled_summary["mean_ms"] / enabled_summary["mean_ms"], 2)

    report = {
        "workload": {
            "total_requests_per_trial": len(queries),
            "unique_queries": len(set(queries)),
            "repetition_ratio": round(1.0 - (len(set(queries)) / len(queries)), 2),
            "trials": trials,
            "cache_max_entries": max_entries,
            "eligible_documents_count": len(eligible_docs),
        },
        "cache_disabled": {
            "total_retrievals": disabled_call_count,
            "latency": disabled_summary,
        },
        "cache_enabled": {
            "total_retrievals": enabled_compute_count,
            "latency": enabled_summary,
            "cache_stats": stats,
        },
        "performance": {
            "speedup_factor": f"{speedup}x",
            "latency_reduction_percent": (
                f"{round((1 - (enabled_summary['mean_ms'] / disabled_summary['mean_ms'])) * 100, 1)}%"
                if disabled_summary["mean_ms"]
                else "0%"
            ),
            "retrieval_call_reduction_percent": (
                f"{round((1 - (enabled_compute_count / disabled_call_count)) * 100, 1)}%"
                if disabled_call_count
                else "0%"
            ),
        },
    }

    target_file = output_path or os.path.join(
        os.path.dirname(__file__), "baseline_retrieval_cache_benchmark.json"
    )
    os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report = run_retrieval_benchmark()
    print("Retrieval Cache Benchmark Report:")
    print(json.dumps(report, indent=2))
