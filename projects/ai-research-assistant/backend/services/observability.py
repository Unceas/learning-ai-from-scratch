"""Observability utilities for stage-level timing, telemetry, and performance tracking in RAG pipeline."""

import logging
import statistics
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from typing import Any

logger = logging.getLogger("research_assistant")


class PerformanceTracker:
    """Thread-safe in-memory telemetry tracker for stage-level latencies and percentile aggregation."""

    def __init__(self, max_samples: int = 1000):
        self._max_samples = max_samples
        self._samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=self._max_samples))
        self._outcomes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._lock = threading.Lock()

    def record(
        self,
        stage: str,
        duration_ms: float,
        outcome: str = "success",
        request_id: str | None = None,
    ) -> None:
        """Record a single stage duration observation."""
        with self._lock:
            self._samples[stage].append(duration_ms)
            self._outcomes[stage][outcome] += 1

    def get_percentiles(self, stage: str) -> dict[str, Any]:
        """Calculate P50, P90, P95, P99, mean, min, max, and sample count for a stage."""
        with self._lock:
            raw = list(self._samples.get(stage, []))
            outcomes = dict(self._outcomes.get(stage, {}))

        if not raw:
            return {
                "stage": stage,
                "count": 0,
                "mean_ms": 0.0,
                "median_ms": 0.0,
                "p50_ms": 0.0,
                "p90_ms": 0.0,
                "p95_ms": 0.0,
                "p99_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "outcomes": outcomes,
            }

        sorted_samples = sorted(raw)
        n = len(sorted_samples)

        def _p(pct: float) -> float:
            idx = min(n - 1, int(n * pct))
            return round(sorted_samples[idx], 2)

        return {
            "stage": stage,
            "count": n,
            "mean_ms": round(statistics.mean(sorted_samples), 2),
            "median_ms": round(statistics.median(sorted_samples), 2),
            "p50_ms": _p(0.50),
            "p90_ms": _p(0.90),
            "p95_ms": _p(0.95),
            "p99_ms": _p(0.99),
            "min_ms": round(min(sorted_samples), 2),
            "max_ms": round(max(sorted_samples), 2),
            "outcomes": outcomes,
        }

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Return percentiles for all recorded stages."""
        with self._lock:
            stages = list(self._samples.keys())
        return {stage: self.get_percentiles(stage) for stage in stages}

    def clear(self) -> None:
        """Reset all recorded telemetry data."""
        with self._lock:
            self._samples.clear()
            self._outcomes.clear()


performance_tracker = PerformanceTracker()


@contextmanager
def measure_stage(
    stage_name: str,
    metrics: dict[str, Any] | None = None,
    request_id: str | None = None,
):
    """Context manager measuring execution duration of a synchronous pipeline stage.

    Args:
        stage_name: Identifier name of the stage (e.g. 'retrieval', 'reranking').
        metrics: Optional dictionary where stage duration in milliseconds is stored.
        request_id: Optional correlation ID for tracing.
    """
    start = time.perf_counter()
    outcome = "success"

    try:
        yield
    except Exception:
        outcome = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        duration_rounded = round(elapsed_ms, 2)

        if metrics is not None:
            metrics[stage_name] = duration_rounded

        performance_tracker.record(
            stage=stage_name,
            duration_ms=duration_rounded,
            outcome=outcome,
            request_id=request_id,
        )

        log_extra = {
            "stage": stage_name,
            "duration_ms": duration_rounded,
            "outcome": outcome,
        }
        if request_id:
            log_extra["request_id"] = request_id

        logger.info("performance_stage", extra=log_extra)


@asynccontextmanager
async def async_measure_stage(
    stage_name: str,
    metrics: dict[str, Any] | None = None,
    request_id: str | None = None,
):
    """Async context manager measuring execution duration of an asynchronous pipeline stage.

    Args:
        stage_name: Identifier name of the stage.
        metrics: Optional dictionary where stage duration in milliseconds is stored.
        request_id: Optional correlation ID for tracing.
    """
    start = time.perf_counter()
    outcome = "success"

    try:
        yield
    except Exception:
        outcome = "error"
        raise
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        duration_rounded = round(elapsed_ms, 2)

        if metrics is not None:
            metrics[stage_name] = duration_rounded

        performance_tracker.record(
            stage=stage_name,
            duration_ms=duration_rounded,
            outcome=outcome,
            request_id=request_id,
        )

        log_extra = {
            "stage": stage_name,
            "duration_ms": duration_rounded,
            "outcome": outcome,
        }
        if request_id:
            log_extra["request_id"] = request_id

        logger.info("performance_stage", extra=log_extra)


def benchmark(fn: Callable[[], Any], iterations: int = 20) -> dict[str, Any]:
    """Execute microbenchmark on a synchronous callable and return timing statistics."""
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        durations.append((time.perf_counter() - start) * 1000)
    durations.sort()
    return {
        "iterations": iterations,
        "mean_ms": round(statistics.mean(durations), 2),
        "median_ms": round(statistics.median(durations), 2),
        "p50_ms": round(statistics.median(durations), 2),
        "p95_ms": round(
            durations[min(len(durations) - 1, int(len(durations) * 0.95))], 2
        ),
        "p99_ms": round(
            durations[min(len(durations) - 1, int(len(durations) * 0.99))], 2
        ),
        "min_ms": round(min(durations), 2),
        "max_ms": round(max(durations), 2),
    }
