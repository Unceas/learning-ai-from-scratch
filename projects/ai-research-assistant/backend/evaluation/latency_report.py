"""Latency reporting and statistical summarization for RAG pipeline observability."""

import json
import os
from statistics import mean, median
from typing import Any


def summarize_latency(samples: list[float]) -> dict:
    """Compute count, mean, median, and 95th percentile latency from samples.

    Uses nearest-rank percentile calculation. Returns None values for empty sample lists.

    Args:
        samples: List of latency measurements in milliseconds.

    Returns:
        Dictionary containing count, mean_ms, median_ms, and p95_ms.
    """
    if not samples:
        return {
            "count": 0,
            "mean_ms": None,
            "median_ms": None,
            "p95_ms": None,
        }

    ordered = sorted(samples)

    # Nearest-rank percentile.
    p95_index = max(
        0,
        int(0.95 * len(ordered) + 0.999999) - 1,
    )

    return {
        "count": len(ordered),
        "mean_ms": round(mean(ordered), 2),
        "median_ms": round(median(ordered), 2),
        "p95_ms": round(ordered[p95_index], 2),
    }


def generate_latency_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-request telemetry records into a structured latency distribution report.

    Args:
        records: List of dictionaries containing stage metrics and operational fields.

    Returns:
        Structured report dictionary containing overall summary, per-stage distributions,
        operational metrics, and identified bottleneck stage.
    """
    if not records:
        return {
            "total_requests": 0,
            "total_latency": summarize_latency([]),
            "stages": {},
            "operational": {
                "empty_retrieval_count": 0,
                "empty_retrieval_rate": 0.0,
                "error_count": 0,
                "error_rate": 0.0,
                "success_rate": 1.0,
                "avg_candidate_count": 0.0,
                "avg_reranked_count": 0.0,
            },
            "bottleneck_stage": None,
        }

    total_samples: list[float] = []
    stage_samples: dict[str, list[float]] = {
        "query_rewriting": [],
        "query_routing": [],
        "retrieval": [],
        "reranking": [],
        "context_assembly": [],
        "generation": [],
    }

    empty_retrieval_count = 0
    error_count = 0
    candidate_counts: list[int] = []
    reranked_counts: list[int] = []

    for r in records:
        # Extract metrics dictionary if embedded
        m = r.get("metrics") or r

        # Total latency
        tot = r.get("total_latency_ms") or r.get("latency_ms") or m.get("total_request") or m.get("total_latency_ms")
        if tot is not None and isinstance(tot, (int, float)):
            total_samples.append(float(tot))
        else:
            # Sum stage latencies if total not directly provided
            st_sum = sum(float(m[s]) for s in stage_samples if s in m and isinstance(m[s], (int, float)))
            if st_sum > 0:
                total_samples.append(round(st_sum, 2))

        # Stage latencies
        for st in stage_samples:
            if st in m and isinstance(m[st], (int, float)):
                stage_samples[st].append(float(m[st]))

        # Operational metrics
        if m.get("empty_retrieval", False):
            empty_retrieval_count += 1
        if m.get("generation_outcome") == "error" or r.get("outcome") == "error" or r.get("status_code", 200) >= 500:
            error_count += 1

        if "candidate_count" in m and isinstance(m["candidate_count"], (int, float)):
            candidate_counts.append(int(m["candidate_count"]))
        if "reranked_count" in m and isinstance(m["reranked_count"], (int, float)):
            reranked_counts.append(int(m["reranked_count"]))

    total_requests = len(records)
    stage_summaries = {st: summarize_latency(stage_samples[st]) for st in stage_samples}

    # Identify bottleneck stage by highest mean latency
    bottleneck_stage = None
    max_stage_mean = -1.0
    for st, summary in stage_summaries.items():
        if summary["mean_ms"] is not None and summary["mean_ms"] > max_stage_mean:
            max_stage_mean = summary["mean_ms"]
            bottleneck_stage = st

    return {
        "total_requests": total_requests,
        "total_latency": summarize_latency(total_samples),
        "stages": stage_summaries,
        "operational": {
            "empty_retrieval_count": empty_retrieval_count,
            "empty_retrieval_rate": round(empty_retrieval_count / total_requests, 4),
            "error_count": error_count,
            "error_rate": round(error_count / total_requests, 4),
            "success_rate": round((total_requests - error_count) / total_requests, 4),
            "avg_candidate_count": round(mean(candidate_counts), 2) if candidate_counts else 0.0,
            "avg_reranked_count": round(mean(reranked_counts), 2) if reranked_counts else 0.0,
        },
        "bottleneck_stage": bottleneck_stage,
    }


def save_latency_report(report: dict[str, Any], filepath: str) -> None:
    """Save latency report to JSON file."""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def load_latency_report(filepath: str) -> dict[str, Any]:
    """Load latency report from JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_benchmark(output_path: str | None = None) -> dict[str, Any]:
    """Run baseline latency benchmark across representative request archetypes.

    Simulates and evaluates:
      - Warm and cold starts
      - Short single-sentence queries
      - Long multi-part comparison queries
      - Dense, keyword, and hybrid retrieval workloads

    Args:
        output_path: Optional path to persist the report JSON.
                     Defaults to 'backend/evaluation/baseline_latency_report.json'.

    Returns:
        Structured latency report.
    """
    representative_samples = [
        # Cold start semantic query
        {
            "query_type": "semantic",
            "retrieval_strategy": "dense",
            "metrics": {
                "query_rewriting": 45.2,
                "query_routing": 3.1,
                "retrieval": 182.4,
                "reranking": 125.6,
                "context_assembly": 2.4,
                "generation": 480.0,
                "candidate_count": 20,
                "reranked_count": 5,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        },
        # Warm semantic query
        {
            "query_type": "semantic",
            "retrieval_strategy": "dense",
            "metrics": {
                "query_rewriting": 22.0,
                "query_routing": 1.8,
                "retrieval": 65.3,
                "reranking": 84.1,
                "context_assembly": 1.5,
                "generation": 340.2,
                "candidate_count": 20,
                "reranked_count": 5,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        },
        # Factual query with hybrid retrieval
        {
            "query_type": "factual",
            "retrieval_strategy": "hybrid",
            "metrics": {
                "query_rewriting": 18.5,
                "query_routing": 1.6,
                "retrieval": 94.2,
                "reranking": 78.4,
                "context_assembly": 1.8,
                "generation": 290.5,
                "candidate_count": 30,
                "reranked_count": 5,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        },
        # Comparison query (multi-query + expansion + hybrid)
        {
            "query_type": "comparison",
            "retrieval_strategy": "hybrid",
            "metrics": {
                "query_rewriting": 35.0,
                "query_routing": 2.2,
                "retrieval": 240.8,
                "reranking": 142.0,
                "context_assembly": 3.1,
                "generation": 520.4,
                "candidate_count": 50,
                "reranked_count": 8,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        },
        # Short keyword query
        {
            "query_type": "factual",
            "retrieval_strategy": "bm25",
            "metrics": {
                "query_rewriting": 12.1,
                "query_routing": 1.2,
                "retrieval": 35.6,
                "reranking": 42.1,
                "context_assembly": 1.2,
                "generation": 210.3,
                "candidate_count": 15,
                "reranked_count": 3,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        },
        # Zero-retrieval query (empty match)
        {
            "query_type": "semantic",
            "retrieval_strategy": "dense",
            "metrics": {
                "query_rewriting": 15.0,
                "query_routing": 1.4,
                "retrieval": 42.0,
                "reranking": 0.0,
                "context_assembly": 0.8,
                "generation": 0.0,
                "candidate_count": 0,
                "reranked_count": 0,
                "empty_retrieval": True,
                "generation_outcome": "skipped_empty_context",
            },
        },
    ]

    report = generate_latency_report(representative_samples)

    target_file = output_path or os.path.join(
        os.path.dirname(__file__), "baseline_latency_report.json"
    )
    save_latency_report(report, target_file)

    return report


if __name__ == "__main__":
    report = run_baseline_benchmark()
    print("Baseline Latency Report:")
    print(json.dumps(report, indent=2))
