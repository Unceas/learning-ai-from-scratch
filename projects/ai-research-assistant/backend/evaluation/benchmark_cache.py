"""Benchmark comparing embedding performance with and without bounded LRU caching."""

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

from backend.evaluation.latency_report import summarize_latency
from backend.services.embedding_cache import EmbeddingCache


def run_embedding_benchmark(
    embed_compute: Optional[Callable[[str], List[float]]] = None,
    queries: Optional[List[str]] = None,
    trials: int = 5,
    max_entries: int = 128,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute comparative benchmark between cache-disabled and cache-enabled workloads.

    Args:
        embed_compute: Function simulating or executing embedding inference.
                       Defaults to realistic mock embedding function with synthetic compute cost.
        queries: List of query texts to embed. Defaults to representative research queries with repetition.
        trials: Number of trials to run for statistical stability.
        max_entries: Cache size.
        output_path: Optional JSON output path.

    Returns:
        Structured benchmark report with latencies, speedups, and cache statistics.
    """
    if embed_compute is None:
        def simulated_compute(text: str) -> List[float]:
            # Simulate embedding vector computation (e.g. matrix ops/tokenization)
            time.sleep(0.002)  # 2ms per compute
            return [float(ord(c) % 10) for c in text[:16]]
        embed_compute = simulated_compute

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
        queries = (base_queries * 5)

    # 1. Warm-up
    for q in queries[:2]:
        embed_compute(q)

    # 2. Run Cache Disabled Workload
    disabled_call_count = 0
    disabled_durations: List[float] = []

    def run_disabled_trial():
        nonlocal disabled_call_count
        start = time.perf_counter()
        for q in queries:
            embed_compute(q)
            disabled_call_count += 1
        return (time.perf_counter() - start) * 1000

    disabled_trial_times = [run_disabled_trial() for _ in range(trials)]

    # 3. Run Cache Enabled Workload
    cache = EmbeddingCache(max_entries=max_entries)
    enabled_compute_count = 0

    def compute_with_counter(text: str) -> List[float]:
        nonlocal enabled_compute_count
        enabled_compute_count += 1
        return embed_compute(text)

    def run_enabled_trial():
        start = time.perf_counter()
        for q in queries:
            cache.get_or_compute(
                q,
                compute_with_counter,
                model_version="benchmark-v1",
                namespace="user:benchmark",
            )
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
        },
        "cache_disabled": {
            "total_computations": disabled_call_count,
            "latency": disabled_summary,
        },
        "cache_enabled": {
            "total_computations": enabled_compute_count,
            "latency": enabled_summary,
            "cache_stats": stats,
        },
        "performance": {
            "speedup_factor": f"{speedup}x",
            "latency_reduction_percent": f"{round((1 - (enabled_summary['mean_ms'] / disabled_summary['mean_ms'])) * 100, 1)}%" if disabled_summary["mean_ms"] else "0%",
            "computation_reduction_percent": f"{round((1 - (enabled_compute_count / disabled_call_count)) * 100, 1)}%" if disabled_call_count else "0%",
        },
    }

    target_file = output_path or os.path.join(
        os.path.dirname(__file__), "baseline_cache_benchmark.json"
    )
    os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report = run_embedding_benchmark()
    print("Embedding Cache Benchmark Report:")
    print(json.dumps(report, indent=2))
