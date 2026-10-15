"""Suite #44: Caching & Redundant-Work Reduction Tests.

Validates:
1. Thread-safe bounded in-memory LRU EmbeddingCache (hits, misses, evictions, copies).
2. Model-version and user-namespace security isolation.
3. EmbeddingService integration across queries and document batches.
4. Retention of multi-tenant authorization during retrieval.
5. Performance benchmarking verifying repeated computation reduction and speedup.
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.services.embedding_cache import EmbeddingCache
from backend.services.embedding_service import EmbeddingService, embed_text, embedding_cache
from backend.evaluation.benchmark_cache import run_embedding_benchmark


class TestCachingAndRedundantWork(unittest.TestCase):
    """Test suite for Day 164 caching and redundant work reduction."""

    def setUp(self):
        # Reset global cache state before each test
        embedding_cache.clear()
        embedding_cache.reset_stats()

    # -------------------------------------------------------------
    # Phase 1: EmbeddingCache Core Data Structure & Policies
    # -------------------------------------------------------------
    def test_repeated_text_uses_cached_embedding(self):
        """Repeated text under same model and namespace returns cached vector without recomputing."""
        cache = EmbeddingCache(max_entries=10)
        calls = []

        def compute(text):
            calls.append(text)
            return [1.0, 2.0, 3.0]

        first = cache.get_or_compute("attention", compute, model_version="v1")
        second = cache.get_or_compute("attention", compute, model_version="v1")

        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)
        self.assertEqual(cache.stats()["hits"], 1)
        self.assertEqual(cache.stats()["misses"], 1)

    def test_model_version_separates_entries(self):
        """Different model versions create distinct keys and prevent reusing stale vectors."""
        cache = EmbeddingCache()
        calls = []

        def compute(text):
            calls.append(text)
            return [float(len(text))]

        cache.get_or_compute("attention", compute, model_version="v1")
        cache.get_or_compute("attention", compute, model_version="v2")

        self.assertEqual(len(calls), 2)
        self.assertEqual(cache.stats()["misses"], 2)
        self.assertEqual(cache.stats()["hits"], 0)

    def test_cache_evicts_oldest_entry(self):
        """Cache strictly bounds entries and evicts least recently used items."""
        cache = EmbeddingCache(max_entries=2)

        def compute(text):
            return [float(len(text))]

        for text in ["a", "b", "c"]:
            cache.get_or_compute(text, compute, model_version="v1")

        stats = cache.stats()
        self.assertEqual(stats["entries"], 2)
        self.assertEqual(stats["evictions"], 1)

    def test_cached_vectors_are_not_mutable_by_callers(self):
        """Returned vectors are independent copies; mutating them does not corrupt the cache."""
        cache = EmbeddingCache()

        def compute(text):
            return [1.0, 2.0]

        vector = cache.get_or_compute("attention", compute, model_version="v1")
        vector[0] = 999.0

        again = cache.get_or_compute("attention", compute, model_version="v1")
        self.assertEqual(again, [1.0, 2.0])

    def test_user_namespaces_prevent_cross_tenant_cache_sharing(self):
        """Separate namespaces for user:alice and user:bob compute independently."""
        cache = EmbeddingCache()
        calls = []

        def compute(text):
            calls.append(text)
            return [4.0, 5.0]

        vec_alice = cache.get_or_compute(
            "confidential research prompt",
            compute,
            model_version="v1",
            namespace="user:alice",
        )
        vec_bob = cache.get_or_compute(
            "confidential research prompt",
            compute,
            model_version="v1",
            namespace="user:bob",
        )

        self.assertEqual(vec_alice, vec_bob)
        self.assertEqual(len(calls), 2)
        self.assertEqual(cache.stats()["misses"], 2)
        self.assertEqual(cache.stats()["hits"], 0)

    def test_clear_and_reset_stats(self):
        """Verify clear purges cache and reset_stats resets telemetry counters."""
        cache = EmbeddingCache()
        cache.get_or_compute("test", lambda t: [1.0], model_version="v1")
        self.assertEqual(cache.stats()["entries"], 1)
        self.assertEqual(cache.stats()["misses"], 1)

        cache.clear()
        self.assertEqual(cache.stats()["entries"], 0)

        cache.reset_stats()
        stats = cache.stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 0)

    def test_get_or_compute_batch_handles_partial_hits(self):
        """Batch embedding lookup handles mix of cached and non-cached texts preserving order."""
        cache = EmbeddingCache(max_entries=10)
        batch_calls = []

        def compute_batch(missing):
            batch_calls.append(list(missing))
            return [[float(len(t))] for t in missing]

        # Warm up "cat"
        cache.get_or_compute("cat", lambda t: [float(len(t))], model_version="v1")

        # Query ["cat", "elephant", "dog"]
        results = cache.get_or_compute_batch(
            ["cat", "elephant", "dog"],
            compute_batch,
            model_version="v1",
        )

        self.assertEqual(results, [[3.0], [8.0], [3.0]])
        self.assertEqual(batch_calls, [["elephant", "dog"]])
        self.assertEqual(cache.stats()["hits"], 1)
        self.assertEqual(cache.stats()["misses"], 3)

    def test_concurrent_access_thread_safety(self):
        """Multiple threads concurrently querying the cache without data corruption."""
        cache = EmbeddingCache(max_entries=20)

        def compute(text):
            return [float(len(text))]

        def worker(w_id):
            for i in range(15):
                text = f"query_{i % 4}"
                cache.get_or_compute(text, compute, model_version="v1", namespace=f"user:{w_id % 2}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = cache.stats()
        self.assertLessEqual(stats["entries"], 20)
        self.assertEqual(stats["hits"] + stats["misses"], 6 * 15)

    # -------------------------------------------------------------
    # Phase 2: EmbeddingService Integration
    # -------------------------------------------------------------
    def test_embedding_service_embed_query_caching(self):
        """Verify EmbeddingService.embed_query uses the global bounded cache with user namespaces."""
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1, 0.2, 0.3]])

        service = EmbeddingService()
        with patch.object(EmbeddingService, "_model", mock_model):
            # First call: cache miss
            vec1 = service.embed_query("What is self-attention?", user_id="user_123")
            self.assertEqual(vec1, [0.1, 0.2, 0.3])
            self.assertEqual(mock_model.encode.call_count, 1)

            # Second call: cache hit
            vec2 = service.embed_query("What is self-attention?", user_id="user_123")
            self.assertEqual(vec2, [0.1, 0.2, 0.3])
            self.assertEqual(mock_model.encode.call_count, 1)

            # Different user: cache miss
            vec3 = service.embed_query("What is self-attention?", user_id="user_456")
            self.assertEqual(vec3, [0.1, 0.2, 0.3])
            self.assertEqual(mock_model.encode.call_count, 2)

    def test_embed_text_helper_function(self):
        """Verify standalone embed_text helper delegates properly to cached service."""
        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.5, 0.6]])

        with patch.object(EmbeddingService, "_model", mock_model):
            v1 = embed_text("Transformer architecture", user_id="test_user")
            v2 = embed_text("Transformer architecture", user_id="test_user")

            self.assertEqual(v1, [0.5, 0.6])
            self.assertEqual(v2, [0.5, 0.6])
            self.assertEqual(mock_model.encode.call_count, 1)

    # -------------------------------------------------------------
    # Phase 3: Authorization & Retrieval Isolation Guard
    # -------------------------------------------------------------
    def test_retrieval_maintains_strict_tenant_isolation_with_caching(self):
        """Confirm that cached vector computation never bypasses document ownership in retrieval."""
        from retrieval import db_retrieve

        mock_db = MagicMock()

        # Simulate user A has document 1, user B has NO documents
        with patch("retrieval.get_indexed_document_ids") as mock_get_docs, \
             patch("backend.services.embedding_service.EmbeddingService.model") as mock_model, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_model.encode.return_value = MagicMock(tolist=lambda: [[0.1, 0.2]])

            # User A query
            mock_get_docs.return_value = [1]
            mock_vs_instance = MagicMock()
            mock_vs_instance.search.return_value = {
                "documents": [["User A confidential text"]],
                "metadatas": [[{"document_id": 1, "filename": "doc_a.pdf"}]],
                "distances": [[0.1]],
            }
            mock_vs_cls.return_value = mock_vs_instance

            results_a = db_retrieve(db=mock_db, user_id="user_a", query="secret query")
            self.assertEqual(len(results_a), 1)
            self.assertEqual(results_a[0]["filename"], "doc_a.pdf")

            # User B submits identical query (which might hit cache for vectors),
            # but User B has NO indexed documents: retrieval returns empty list immediately!
            mock_get_docs.return_value = []
            results_b = db_retrieve(db=mock_db, user_id="user_b", query="secret query")
            self.assertEqual(results_b, [])

    # -------------------------------------------------------------
    # Phase 4: Performance Benchmark Execution
    # -------------------------------------------------------------
    def test_run_embedding_benchmark_produces_valid_report(self):
        """Verify run_embedding_benchmark measures cache speedup and generates JSON report."""
        test_output = "backend/evaluation/test_cache_benchmark.json"
        try:
            report = run_embedding_benchmark(
                trials=3,
                max_entries=64,
                output_path=test_output,
            )

            self.assertIn("workload", report)
            self.assertIn("cache_disabled", report)
            self.assertIn("cache_enabled", report)
            self.assertIn("performance", report)

            # Validate that caching reduced computation
            self.assertLess(
                report["cache_enabled"]["total_computations"],
                report["cache_disabled"]["total_computations"],
            )

            # Check JSON file written
            self.assertTrue(os.path.exists(test_output))
        finally:
            if os.path.exists(test_output):
                os.remove(test_output)


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING SUITE #44: CACHING & REDUNDANT-WORK REDUCTION")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCachingAndRedundantWork)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "=" * 60)
        print("SUITE #44 COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("SUITE #44 FAILED!")
        print("=" * 60)
        sys.exit(1)
