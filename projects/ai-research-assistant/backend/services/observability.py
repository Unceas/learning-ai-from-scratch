"""Observability utilities for stage-level timing and telemetry in RAG pipeline."""

import logging
import time
from contextlib import asynccontextmanager, contextmanager

logger = logging.getLogger("research_assistant")


@contextmanager
def measure_stage(stage: str, metrics: dict):
    """Context manager measuring execution duration of a synchronous pipeline stage.

    Args:
        stage: Identifier name of the stage (e.g. 'query_rewriting', 'retrieval').
        metrics: Dictionary where stage duration in milliseconds is stored.
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

        metrics[stage] = round(elapsed_ms, 2)

        logger.info(
            "pipeline_stage",
            extra={
                "stage": stage,
                "duration_ms": round(elapsed_ms, 2),
                "outcome": outcome,
            },
        )


@asynccontextmanager
async def async_measure_stage(stage: str, metrics: dict):
    """Async context manager measuring execution duration of an asynchronous pipeline stage.

    Args:
        stage: Identifier name of the stage.
        metrics: Dictionary where stage duration in milliseconds is stored.
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

        metrics[stage] = round(elapsed_ms, 2)

        logger.info(
            "pipeline_stage",
            extra={
                "stage": stage,
                "duration_ms": round(elapsed_ms, 2),
                "outcome": outcome,
            },
        )
