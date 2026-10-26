"""Benchmark evaluating system throughput and latency distributions across increasing concurrency levels."""

import asyncio
import json
import os
import sys
import time
from collections.abc import Callable
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.evaluation.latency_report import summarize_latency
from backend.services.async_generator import AsyncGenerator
from backend.services.concurrent_retrieval import retrieve_queries_async


def run_concurrency_benchmark(
    concurrency_levels: list[int] | None = None,
    requests_per_level: int = 20,
    simulated_pipeline_fn: Callable[[str], Any] | None = None,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Execute comparative concurrency benchmark measuring throughput, latency, and error rates.

    Args:
        concurrency_levels: List of concurrency limits to evaluate (e.g. [1, 2, 5, 10]).
        requests_per_level: Total requests dispatched per concurrency level.
        simulated_pipeline_fn: Async function representing full RAG/Chat request lifecycle.
        output_path: Destination JSON filepath for baseline report.

    Returns:
        Structured concurrency benchmark report.
    """
    if concurrency_levels is None:
        concurrency_levels = [1, 2, 5, 10]

    async def default_pipeline(query: str) -> dict[str, Any]:
        # Stage 1: Async query rewriting simulation (network I/O, ~10ms)
        await asyncio.sleep(0.01)

        # Stage 2: Parallel candidate retrieval across 2 subqueries (~15ms)
        async def mock_subquery_retrieve(sub_q: str) -> list[dict[str, Any]]:
            await asyncio.sleep(0.015)
            return [{"text": f"Passage for {sub_q}", "score": 0.88}]

        candidates = await retrieve_queries_async(
            [f"{query} sub-1", f"{query} sub-2"],
            mock_subquery_retrieve,
            max_concurrency=4,
            timeout=5.0,
        )

        # Stage 3: Reranker / context assembly simulation (CPU, ~5ms)
        await asyncio.sleep(0.005)

        # Stage 4: LLM generation simulation (bounded by async generator, ~20ms)
        async def mock_llm_call(prompt: str) -> str:
            await asyncio.sleep(0.02)
            return "Generated research answer."

        gen = AsyncGenerator(client=mock_llm_call, max_concurrency=8, timeout=10.0)
        answer = await gen.generate(query)

        return {"answer": answer, "candidates_count": sum(len(c) for c in candidates)}

    pipeline = simulated_pipeline_fn or default_pipeline

    queries = [
        "What is multi-head self-attention?",
        "Explain FlashAttention memory optimizations.",
        "Compare BERT encoder and GPT autoregressive decoder.",
        "What is Reciprocal Rank Fusion?",
        "How does parameter-efficient fine-tuning work?",
    ]

    results_by_level: dict[str, Any] = {}
    baseline_throughput = 0.0

    async def run_level(concurrency: int) -> dict[str, Any]:
        sem = asyncio.Semaphore(concurrency)
        latencies: list[float] = []
        errors = 0

        async def worker(req_idx: int):
            nonlocal errors
            q = queries[req_idx % len(queries)]
            async with sem:
                start = time.perf_counter()
                try:
                    await pipeline(q)
                    duration_ms = (time.perf_counter() - start) * 1000
                    latencies.append(duration_ms)
                except Exception:
                    errors += 1

        overall_start = time.perf_counter()
        tasks = [worker(i) for i in range(requests_per_level)]
        await asyncio.gather(*tasks)
        total_time_s = time.perf_counter() - overall_start

        latency_summary = summarize_latency(latencies)
        completed = len(latencies)
        throughput = round(completed / total_time_s, 2) if total_time_s > 0 else 0.0
        error_rate = round((errors / requests_per_level) * 100, 2)

        return {
            "concurrency_limit": concurrency,
            "total_requests": requests_per_level,
            "completed_requests": completed,
            "failed_requests": errors,
            "error_rate_percent": error_rate,
            "total_time_seconds": round(total_time_s, 3),
            "throughput_requests_per_second": throughput,
            "latency": latency_summary,
        }

    async def execute_all():
        nonlocal baseline_throughput
        for c in concurrency_levels:
            res = await run_level(c)
            if c == 1:
                baseline_throughput = res["throughput_requests_per_second"]
                res["scaling_factor"] = "1.0x"
            else:
                factor = (
                    round(res["throughput_requests_per_second"] / baseline_throughput, 2)
                    if baseline_throughput > 0
                    else 1.0
                )
                res["scaling_factor"] = f"{factor}x"
            results_by_level[f"concurrency_{c}"] = res

    asyncio.run(execute_all())

    max_factor = max(
        float(r["scaling_factor"].rstrip("x")) for r in results_by_level.values()
    )

    report = {
        "benchmark": "concurrency_scaling_evaluation",
        "requests_per_level": requests_per_level,
        "concurrency_levels": concurrency_levels,
        "results": results_by_level,
        "summary": {
            "baseline_throughput_rps": baseline_throughput,
            "peak_throughput_rps": max(
                r["throughput_requests_per_second"] for r in results_by_level.values()
            ),
            "max_scaling_factor": f"{max_factor}x",
        },
    }

    target_file = output_path or os.path.join(
        os.path.dirname(__file__), "baseline_concurrency_benchmark.json"
    )
    os.makedirs(os.path.dirname(os.path.abspath(target_file)), exist_ok=True)
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report = run_concurrency_benchmark()
    print("Concurrency Benchmark Report:")
    print(json.dumps(report, indent=2))
