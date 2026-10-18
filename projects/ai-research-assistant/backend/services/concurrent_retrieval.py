"""Concurrent retrieval utilities for parallelizing independent subquery searches."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)


def retrieve_queries_concurrent(
    queries: List[str],
    retrieve_fn: Callable[[str], List[Dict[str, Any]]],
    max_workers: Optional[int] = None,
    timeout: Optional[float] = None,
) -> List[List[Dict[str, Any]]]:
    """Execute independent candidate retrieval queries concurrently using a bounded thread pool.

    Guarantees:
    - Results maintain the exact same index order as the input queries list.
    - Bounded worker pool prevents thread exhaustion under burst traffic.
    - Enforces per-query timeout to prevent slow/hung downstream providers from blocking execution.
    - Partial failures on individual queries log warnings and yield empty candidate lists
      without discarding successful results from sibling queries.

    Args:
        queries: List of independent query strings to retrieve.
        retrieve_fn: Retrieval function callable taking a single query string.
        max_workers: Maximum concurrent retrieval threads (defaults to settings).
        timeout: Maximum execution timeout in seconds per query.

    Returns:
        List of candidate lists, aligned to the input queries order.
    """
    if not queries:
        return []

    if len(queries) == 1:
        try:
            return [retrieve_fn(queries[0])]
        except Exception as exc:
            logger.warning("Single retrieval query '%s' failed: %s", queries[0], exc)
            return [[]]

    workers = (
        max_workers
        if max_workers is not None
        else getattr(settings, "max_concurrent_retrieval_workers", 4)
    )
    workers = max(1, min(workers, len(queries)))
    exec_timeout = (
        timeout
        if timeout is not None
        else getattr(settings, "retrieval_timeout_seconds", 15.0)
    )

    results: List[Optional[List[Dict[str, Any]]]] = [None] * len(queries)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_idx = {
            executor.submit(retrieve_fn, q): idx
            for idx, q in enumerate(queries)
        }

        for future in as_completed(future_to_idx, timeout=exec_timeout + 5.0):
            idx = future_to_idx[future]
            q = queries[idx]
            try:
                res = future.result(timeout=exec_timeout)
                results[idx] = res if isinstance(res, list) else []
            except TimeoutError:
                logger.warning("Retrieval for query '%s' timed out after %.1fs", q, exec_timeout)
                results[idx] = []
            except Exception as exc:
                logger.warning("Retrieval for query '%s' encountered an error: %s", q, exc)
                results[idx] = []

    # Replace any unpopulated entries with empty lists
    return [r if r is not None else [] for r in results]


async def retrieve_queries_async(
    queries: List[str],
    retrieve_fn: Callable[[str], Any],
    max_concurrency: Optional[int] = None,
    timeout: Optional[float] = None,
) -> List[List[Dict[str, Any]]]:
    """Execute independent candidate retrieval queries concurrently using asyncio.

    Supports both coroutine and synchronous retrieval functions (offloaded to threadpool).
    """
    if not queries:
        return []

    concurrency = (
        max_concurrency
        if max_concurrency is not None
        else getattr(settings, "max_concurrent_retrieval_workers", 4)
    )
    sem = asyncio.Semaphore(concurrency)
    exec_timeout = (
        timeout
        if timeout is not None
        else getattr(settings, "retrieval_timeout_seconds", 15.0)
    )

    async def _safe_retrieve_one(q: str) -> List[Dict[str, Any]]:
        async with sem:
            try:
                if asyncio.iscoroutinefunction(retrieve_fn):
                    coro = retrieve_fn(q)
                else:
                    coro = asyncio.to_thread(retrieve_fn, q)

                res = await asyncio.wait_for(coro, timeout=exec_timeout)
                return res if isinstance(res, list) else []
            except asyncio.TimeoutError:
                logger.warning("Async retrieval for query '%s' timed out after %.1fs", q, exec_timeout)
                return []
            except Exception as exc:
                logger.warning("Async retrieval for query '%s' failed: %s", q, exc)
                return []

    tasks = [_safe_retrieve_one(q) for q in queries]
    return await asyncio.gather(*tasks)
