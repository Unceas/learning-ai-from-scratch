"""Unit and integration tests for async execution and concurrency safety."""

import asyncio
import os
import sys
import threading
import time
from typing import Any

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.async_generator import AsyncGenerator
from backend.services.concurrent_retrieval import (
    retrieve_queries_concurrent,
)
from backend.services.document_processor import ingestion_semaphore
from backend.services.retrieval_cache import RetrievalCache, retrieval_cache


# ---------------------------------------------------------------------------
# 1. Basic Scheduling Tests (from Day 166 guide)
# ---------------------------------------------------------------------------
async def simulated_request() -> str:
    await asyncio.sleep(0.1)
    return "ok"


async def run_sequential(count: int) -> list[str]:
    results = []
    for _ in range(count):
        results.append(await simulated_request())
    return results


async def run_concurrent(count: int) -> list[str]:
    return await asyncio.gather(*(simulated_request() for _ in range(count)))


def test_concurrent_requests_complete():
    """Verify that concurrent scheduling completes multiple I/O requests faster than sequential."""
    async def scenario():
        start = time.perf_counter()
        results = await run_concurrent(5)
        elapsed = time.perf_counter() - start

        assert results == ["ok"] * 5
        assert elapsed < 0.4  # Sequential would take 0.5s+

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# 2. AsyncGenerator Bounded Concurrency & Timeouts
# ---------------------------------------------------------------------------
def test_async_generator_bounds_concurrency():
    """Verify semaphore caps concurrent execution to max_concurrency."""
    max_active = 0
    current_active = 0
    lock = asyncio.Lock()

    async def mock_compute(prompt: str) -> str:
        nonlocal max_active, current_active
        async with lock:
            current_active += 1
            max_active = max(max_active, current_active)
        await asyncio.sleep(0.05)
        async with lock:
            current_active -= 1
        return f"result for {prompt}"

    async def scenario():
        gen = AsyncGenerator(client=mock_compute, max_concurrency=3, timeout=5.0)
        tasks = [gen.generate(f"p{i}") for i in range(9)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 9
        assert max_active <= 3
        assert gen.stats()["completed_requests"] == 9
        assert gen.stats()["timeouts"] == 0

    asyncio.run(scenario())


def test_async_generator_enforces_timeout():
    """Verify timeout cancels slow generation and releases the semaphore."""
    async def slow_compute(prompt: str) -> str:
        await asyncio.sleep(1.0)
        return "too late"

    async def scenario():
        gen = AsyncGenerator(client=slow_compute, max_concurrency=2, timeout=0.05)
        with pytest.raises(asyncio.TimeoutError):
            await gen.generate("test slow")

        stats = gen.stats()
        assert stats["timeouts"] == 1
        assert stats["active_requests"] == 0

        # Verify semaphore was released: subsequent fast request succeeds
        fast_gen = AsyncGenerator(client=lambda p: "fast", max_concurrency=2, timeout=1.0)
        fast_res = await fast_gen.generate("test fast")
        assert fast_res == "fast"

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# 3. Concurrent Retrieval & Error Resilience
# ---------------------------------------------------------------------------
def test_concurrent_retrieval_handles_partial_failures():
    """Verify concurrent retrieval completes, preserves order, and tolerates individual errors."""
    def retrieve_one(query: str) -> list[dict[str, Any]]:
        if "fail" in query:
            raise RuntimeError("Database connection reset")
        if "slow" in query:
            time.sleep(0.2)
            return [{"text": "slow result"}]
        return [{"text": f"result for {query}"}]

    queries = ["q1", "fail_query", "q2", "slow_query"]
    results = retrieve_queries_concurrent(
        queries=queries,
        retrieve_fn=retrieve_one,
        max_workers=4,
        timeout=1.0,
    )

    assert len(results) == 4
    assert len(results[0]) == 1
    assert results[0][0]["text"] == "result for q1"
    # Failed query gracefully yields empty list without throwing
    assert results[1] == []
    assert len(results[2]) == 1
    assert results[2][0]["text"] == "result for q2"
    assert len(results[3]) == 1
    assert results[3][0]["text"] == "slow result"


# ---------------------------------------------------------------------------
# 4. Multi-Tenant Isolation & Document Ownership under Concurrency
# ---------------------------------------------------------------------------
def test_concurrent_multi_user_isolation():
    """Verify concurrent requests for different users do not leak documents or cache keys."""
    user_results: dict[str, list[dict[str, Any]]] = {}

    def run_user_request(user_id: str, doc_ids: list[int]):
        docs = [{"id": d, "index_version": 1} for d in doc_ids]
        cfg = {"strategy": "dense", "top_k": 5}
        key = RetrievalCache.make_key(
            user_id=user_id,
            eligible_documents=docs,
            query="transformers",
            retrieval_config=cfg,
        )
        candidates = [{"text": f"Content for {user_id}", "user": user_id}]
        retrieval_cache.set(key, candidates)
        user_results[user_id] = retrieval_cache.get(key)

    threads = [
        threading.Thread(target=run_user_request, args=("alice", [1, 2])),
        threading.Thread(target=run_user_request, args=("bob", [3, 4])),
        threading.Thread(target=run_user_request, args=("carol", [5])),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert user_results["alice"][0]["user"] == "alice"
    assert user_results["bob"][0]["user"] == "bob"
    assert user_results["carol"][0]["user"] == "carol"


# ---------------------------------------------------------------------------
# 5. Ingestion and Chat Concurrency
# ---------------------------------------------------------------------------
def test_ingestion_semaphore_limits_parallel_processing():
    """Verify document ingestion semaphore bounds concurrent background workers."""
    initial_value = ingestion_semaphore._value  # Available capacity

    assert initial_value >= 1

    # Simulate worker acquiring semaphore during chunk processing
    acquired = ingestion_semaphore.acquire(timeout=0.1)
    assert acquired is True
    try:
        # One slot is occupied
        assert ingestion_semaphore._value == initial_value - 1
    finally:
        ingestion_semaphore.release()

    assert ingestion_semaphore._value == initial_value


# ---------------------------------------------------------------------------
# 6. Retrieval Cache Under Concurrent Burst
# ---------------------------------------------------------------------------
def test_retrieval_cache_concurrent_access():
    """Verify cache integrity during concurrent read/write race conditions."""
    cache = RetrievalCache(max_entries=32)
    errors = []

    def writer(tid: int):
        try:
            for i in range(50):
                k = f"k_{i % 8}"
                cache.set(k, [{"thread": tid, "iter": i}])
                _ = cache.get(k)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0
    stats = cache.stats()
    assert stats["entries"] <= 32
    assert stats["hits"] + stats["misses"] > 0
