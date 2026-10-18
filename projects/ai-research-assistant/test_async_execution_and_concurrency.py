"""Suite #46: Async Execution & Concurrent Requests Tests.

Validates:
1. Asynchronous scheduling and concurrency execution model.
2. AsyncGenerator bounded concurrency semaphore and request timeouts.
3. Thread-safe parallel candidate retrieval across multiple subqueries.
4. Error resilience: partial retrieval failures and timeout isolation.
5. Ingestion concurrency bounding preventing resource starvation of chat requests.
6. Strict multi-tenant isolation under simultaneous user requests.
7. ChatService async_chat worker thread execution.
8. Retrieval cache stability under concurrent burst workloads.
9. Concurrency scaling benchmark execution and reporting.
"""

import asyncio
import json
import os
import sys
import threading
import time
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.services.async_generator import AsyncGenerator, default_async_generator
from backend.services.concurrent_retrieval import retrieve_queries_concurrent, retrieve_queries_async
from backend.services.document_processor import ingestion_semaphore
from backend.services.chat_service import ChatService
from backend.services.retrieval_cache import RetrievalCache, retrieval_cache
from backend.evaluation.benchmark_concurrency import run_concurrency_benchmark


class TestAsyncExecutionModel(unittest.TestCase):
    """Test async execution patterns, scheduling speedups, and bounded generator."""

    def test_scheduling_concurrency_speedup(self):
        """Asynchronous concurrency completes independent tasks significantly faster than sequential."""
        async def work():
            await asyncio.sleep(0.05)
            return "done"

        async def run_test():
            # Sequential
            t0 = time.perf_counter()
            seq_res = [await work() for _ in range(4)]
            seq_time = time.perf_counter() - t0

            # Concurrent
            t1 = time.perf_counter()
            con_res = await asyncio.gather(*(work() for _ in range(4)))
            con_time = time.perf_counter() - t1

            self.assertEqual(seq_res, ["done"] * 4)
            self.assertEqual(con_res, ["done"] * 4)
            self.assertLess(con_time, seq_time * 0.7)

        asyncio.run(run_test())

    def test_async_generator_initialization_and_validation(self):
        """Verify parameter bounds and statistics tracking."""
        gen = AsyncGenerator(max_concurrency=4, timeout=30.0)
        self.assertEqual(gen.max_concurrency, 4)
        self.assertEqual(gen.timeout, 30.0)
        self.assertEqual(gen.stats()["total_requests"], 0)

        with self.assertRaises(ValueError):
            AsyncGenerator(max_concurrency=0)

    def test_async_generator_limits_concurrency(self):
        """Verify semaphore restricts active requests to max_concurrency."""
        max_active = 0
        current_active = 0
        lock = asyncio.Lock()

        async def mock_compute(prompt: str) -> str:
            nonlocal max_active, current_active
            async with lock:
                current_active += 1
                if current_active > max_active:
                    max_active = current_active
            await asyncio.sleep(0.05)
            async with lock:
                current_active -= 1
            return f"res_{prompt}"

        async def run_test():
            gen = AsyncGenerator(client=mock_compute, max_concurrency=2, timeout=5.0)
            tasks = [gen.generate(f"item_{i}") for i in range(6)]
            results = await asyncio.gather(*tasks)

            self.assertEqual(len(results), 6)
            self.assertLessEqual(max_active, 2)
            self.assertEqual(gen.stats()["completed_requests"], 6)

        asyncio.run(run_test())

    def test_async_generator_enforces_timeout(self):
        """Verify timeout cancels slow generation and releases semaphore."""
        async def slow_compute(prompt: str) -> str:
            await asyncio.sleep(0.5)
            return "late"

        async def run_test():
            gen = AsyncGenerator(client=slow_compute, max_concurrency=2, timeout=0.05)
            with self.assertRaises(asyncio.TimeoutError):
                await gen.generate("prompt")

            self.assertEqual(gen.stats()["timeouts"], 1)
            self.assertEqual(gen.stats()["active_requests"], 0)

            # Confirm subsequent request succeeds
            fast_gen = AsyncGenerator(client=lambda p: "ok", max_concurrency=2, timeout=1.0)
            res = await fast_gen.generate("fast")
            self.assertEqual(res, "ok")

        asyncio.run(run_test())


class TestConcurrentRetrieval(unittest.TestCase):
    """Test parallel subquery retrieval, order preservation, and partial failure isolation."""

    def test_concurrent_retrieval_preserves_order(self):
        """Results must maintain exact input index order regardless of execution time."""
        def mock_retrieve(q: str) -> List[Dict[str, Any]]:
            if q == "slow":
                time.sleep(0.08)
                return [{"query": "slow", "score": 0.5}]
            return [{"query": q, "score": 0.9}]

        queries = ["first", "slow", "third"]
        results = retrieve_queries_concurrent(
            queries=queries,
            retrieve_fn=mock_retrieve,
            max_workers=3,
            timeout=2.0,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0][0]["query"], "first")
        self.assertEqual(results[1][0]["query"], "slow")
        self.assertEqual(results[2][0]["query"], "third")

    def test_concurrent_retrieval_handles_partial_failure(self):
        """Individual subquery exceptions must not discard results from other queries."""
        def mock_retrieve(q: str) -> List[Dict[str, Any]]:
            if "fail" in q:
                raise ConnectionError("Vector store timeout")
            return [{"text": f"Doc for {q}"}]

        queries = ["valid_1", "fail_query", "valid_2"]
        results = retrieve_queries_concurrent(
            queries=queries,
            retrieve_fn=mock_retrieve,
            max_workers=3,
            timeout=1.0,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(len(results[0]), 1)
        self.assertEqual(results[1], [])  # Graceful fallback to empty list
        self.assertEqual(len(results[2]), 1)

    def test_async_retrieval_wrapper(self):
        """retrieve_queries_async coordinates async subqueries correctly."""
        async def mock_async_retrieve(q: str) -> List[Dict[str, Any]]:
            await asyncio.sleep(0.02)
            return [{"text": f"Async result for {q}"}]

        async def run_test():
            queries = ["alpha", "beta"]
            res = await retrieve_queries_async(queries, mock_async_retrieve, max_concurrency=2)
            self.assertEqual(len(res), 2)
            self.assertIn("alpha", res[0][0]["text"])
            self.assertIn("beta", res[1][0]["text"])

        asyncio.run(run_test())


class TestConcurrencySafetyAndIsolation(unittest.TestCase):
    """Test multi-tenant isolation, ingestion bounding, session safety, and caching under concurrency."""

    def setUp(self):
        retrieval_cache.clear()
        retrieval_cache.reset_stats()

    def test_multi_user_isolation_under_concurrency(self):
        """Simultaneous queries from User A and User B must remain strictly isolated."""
        results: Dict[str, List[Dict[str, Any]]] = {}

        def query_as_user(user_id: str, doc_ids: List[int]):
            docs = [{"id": d, "index_version": 1} for d in doc_ids]
            cfg = {"strategy": "dense", "top_k": 5}
            key = RetrievalCache.make_key(
                user_id=user_id,
                eligible_documents=docs,
                query="deep learning",
                retrieval_config=cfg,
            )
            # Store mock retrieved candidate
            retrieval_cache.set(key, [{"doc_id": doc_ids[0], "owner": user_id}])
            results[user_id] = retrieval_cache.get(key)

        threads = [
            threading.Thread(target=query_as_user, args=("user_x", [101])),
            threading.Thread(target=query_as_user, args=("user_y", [202])),
            threading.Thread(target=query_as_user, args=("user_z", [303])),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results["user_x"][0]["owner"], "user_x")
        self.assertEqual(results["user_y"][0]["owner"], "user_y")
        self.assertEqual(results["user_z"][0]["owner"], "user_z")

    def test_ingestion_semaphore_protects_chat_resources(self):
        """Document ingestion semaphore caps concurrent parsing and embedding."""
        initial = ingestion_semaphore._value
        self.assertGreaterEqual(initial, 1)

        acquired = ingestion_semaphore.acquire(timeout=0.1)
        self.assertTrue(acquired)
        try:
            self.assertEqual(ingestion_semaphore._value, initial - 1)
        finally:
            ingestion_semaphore.release()

        self.assertEqual(ingestion_semaphore._value, initial)

    def test_chat_service_async_chat_offload(self):
        """ChatService.async_chat executes via worker thread without blocking the event loop."""
        mock_db = MagicMock()
        chat_service = ChatService()

        # Mock synchronous chat method
        with patch.object(chat_service, "chat", return_value={"answer": "Async answer", "conversation_id": 99}):
            async def run_test():
                res = await chat_service.async_chat(
                    db=mock_db,
                    user_id="test_user",
                    message="Hello world",
                )
                self.assertEqual(res["answer"], "Async answer")
                self.assertEqual(res["conversation_id"], 99)

            asyncio.run(run_test())

    def test_retrieval_cache_concurrent_burst(self):
        """RetrievalCache handles simultaneous reads and writes without data race corruption."""
        cache = RetrievalCache(max_entries=16)
        errors = []

        def worker(tid: int):
            try:
                for i in range(40):
                    k = f"burst_key_{i % 8}"
                    cache.set(k, [{"tid": tid, "iter": i}])
                    _ = cache.get(k)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertLessEqual(cache.stats()["entries"], 16)


class TestConcurrencyBenchmark(unittest.TestCase):
    """Verify concurrency benchmark execution and output generation."""

    def test_run_concurrency_benchmark_report(self):
        """run_concurrency_benchmark measures throughput scaling and writes valid JSON."""
        test_output = "backend/evaluation/test_concurrency_benchmark.json"
        try:
            report = run_concurrency_benchmark(
                concurrency_levels=[1, 2],
                requests_per_level=4,
                output_path=test_output,
            )

            self.assertIn("benchmark", report)
            self.assertIn("results", report)
            self.assertIn("concurrency_1", report["results"])
            self.assertIn("concurrency_2", report["results"])

            c1 = report["results"]["concurrency_1"]
            self.assertEqual(c1["total_requests"], 4)
            self.assertGreater(c1["throughput_requests_per_second"], 0)

            self.assertTrue(os.path.exists(test_output))
            with open(test_output, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["requests_per_level"], 4)
        finally:
            if os.path.exists(test_output):
                os.remove(test_output)


if __name__ == "__main__":
    unittest.main()
