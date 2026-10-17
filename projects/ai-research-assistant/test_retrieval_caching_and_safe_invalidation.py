"""Suite #45: Retrieval Caching & Safe Invalidation Tests.

Validates:
1. Thread-safe bounded in-memory LRU RetrievalCache (hits, misses, evictions, copies).
2. Deterministic cache key generation with user isolation, doc versioning, query, and config.
3. Logical cache invalidation via index_version increment during reindexing.
4. Logical cache invalidation via corpus modification during document deletion.
5. Strict tenant isolation preventing cross-user data leakage.
6. db_retrieve and retrieve_candidates caching integration.
7. Performance benchmarking verifying speedup factor and retrieval reduction report.
"""

import json
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.services.retrieval_cache import RetrievalCache, retrieval_cache
from backend.evaluation.benchmark_retrieval_cache import run_retrieval_benchmark
from retrieval import db_retrieve, retrieve_candidates


class TestRetrievalCacheCore(unittest.TestCase):
    """Unit tests for the core RetrievalCache data structure and key hashing."""

    def setUp(self):
        retrieval_cache.clear()
        retrieval_cache.reset_stats()

    def test_cache_initialization_and_validation(self):
        """Verify initialization bounds and parameter validation."""
        cache = RetrievalCache(max_entries=64)
        self.assertEqual(cache.max_entries, 64)
        self.assertEqual(cache.stats()["entries"], 0)

        with self.assertRaises(ValueError):
            RetrievalCache(max_entries=0)

    def test_deterministic_key_hashing_and_order_invariance(self):
        """Identical inputs, regardless of document list order, yield identical SHA-256 keys."""
        docs_order_1 = [{"id": 10, "index_version": 2}, {"id": 20, "index_version": 1}]
        docs_order_2 = [{"id": 20, "index_version": 1}, {"id": 10, "index_version": 2}]

        cfg = {"strategy": "dense", "top_k": 5}

        k1 = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=docs_order_1,
            query="attention mechanism",
            retrieval_config=cfg,
        )
        k2 = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=docs_order_2,
            query="attention mechanism",
            retrieval_config=cfg,
        )
        self.assertEqual(k1, k2)

    def test_key_sensitivity_to_security_boundaries(self):
        """User identity, query, config, doc IDs, and index_version must produce distinct keys."""
        base_docs = [{"id": 1, "index_version": 1}]
        base_cfg = {"strategy": "dense", "top_k": 5}

        base_key = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=base_docs,
            query="attention",
            retrieval_config=base_cfg,
        )

        # 1. Different user
        diff_user = RetrievalCache.make_key(
            user_id="bob",
            eligible_documents=base_docs,
            query="attention",
            retrieval_config=base_cfg,
        )
        self.assertNotEqual(base_key, diff_user)

        # 2. Reindexed doc (index_version increment)
        reindexed_docs = [{"id": 1, "index_version": 2}]
        reindexed_key = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=reindexed_docs,
            query="attention",
            retrieval_config=base_cfg,
        )
        self.assertNotEqual(base_key, reindexed_key)

        # 3. Different doc id
        diff_doc_id = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=[{"id": 2, "index_version": 1}],
            query="attention",
            retrieval_config=base_cfg,
        )
        self.assertNotEqual(base_key, diff_doc_id)

        # 4. Different query
        diff_query = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=base_docs,
            query="recurrent nets",
            retrieval_config=base_cfg,
        )
        self.assertNotEqual(base_key, diff_query)

        # 5. Different retrieval configuration
        diff_config = RetrievalCache.make_key(
            user_id="alice",
            eligible_documents=base_docs,
            query="attention",
            retrieval_config={"strategy": "dense", "top_k": 10},
        )
        self.assertNotEqual(base_key, diff_config)

    def test_cache_hit_miss_and_deep_copy_isolation(self):
        """Verify hit/miss metrics and deep copy protection against caller mutations."""
        cache = RetrievalCache(max_entries=10)
        key = "test_key_abc"

        self.assertIsNone(cache.get(key))
        self.assertEqual(cache.stats()["misses"], 1)

        candidates = [
            {"text": "Sample passage", "score": 0.9, "document_id": 1, "chunk_index": 0}
        ]
        cache.set(key, candidates)

        # Caller mutates input list
        candidates[0]["score"] = 0.0
        candidates.append({"text": "Injected passage"})

        # Cached item must remain untouched
        retrieved = cache.get(key)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["score"], 0.9)
        self.assertEqual(cache.stats()["hits"], 1)

        # Caller mutates retrieved item
        retrieved[0]["text"] = "Tampered text"
        again = cache.get(key)
        self.assertEqual(again[0]["text"], "Sample passage")

    def test_lru_capacity_and_eviction(self):
        """Verify strict LRU capacity eviction and MRU update on access."""
        cache = RetrievalCache(max_entries=2)

        cache.set("k1", [{"id": 1}])
        cache.set("k2", [{"id": 2}])
        self.assertEqual(cache.stats()["entries"], 2)
        self.assertEqual(cache.stats()["evictions"], 0)

        # Touch k1 to make it MRU
        _ = cache.get("k1")

        # Insert k3; k2 should be evicted
        cache.set("k3", [{"id": 3}])
        self.assertEqual(cache.stats()["evictions"], 1)
        self.assertIsNotNone(cache.get("k1"))
        self.assertIsNone(cache.get("k2"))
        self.assertIsNotNone(cache.get("k3"))

    def test_multithreaded_concurrency(self):
        """Ensure thread-safe concurrent reads and writes without errors."""
        cache = RetrievalCache(max_entries=50)

        def worker(w_id: int):
            for i in range(50):
                k = f"k_{w_id}_{i % 5}"
                cache.set(k, [{"worker": w_id, "idx": i}])
                _ = cache.get(k)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = cache.stats()
        self.assertLessEqual(stats["entries"], 50)
        self.assertGreater(stats["hits"] + stats["misses"], 0)


class TestRetrievalCachingIntegration(unittest.TestCase):
    """Integration tests for db_retrieve, retrieve_candidates, and safe invalidation."""

    def setUp(self):
        retrieval_cache.clear()
        retrieval_cache.reset_stats()

    def test_db_retrieve_uses_cache_on_repeated_query(self):
        """Subsequent identical queries hit the cache without vector store search."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.get_eligible_indexed_documents") as mock_get_eligible, \
             patch("backend.services.embedding_service.EmbeddingService.embed_query") as mock_embed, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_get_doc_ids.return_value = [10]
            mock_get_eligible.return_value = [{"id": 10, "index_version": 1}]
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_vs_inst = MagicMock()
            mock_vs_inst.search.return_value = {
                "documents": [["Retrieved text chunk"]],
                "metadatas": [[{"document_id": 10, "filename": "paper.pdf", "chunk_index": 0}]],
                "distances": [[0.1]],
            }
            mock_vs_cls.return_value = mock_vs_inst

            # First retrieval (cache miss)
            res1 = db_retrieve(db=mock_db, user_id="user_a", query="deep learning", top_k=5)
            self.assertEqual(len(res1), 1)
            self.assertEqual(res1[0]["filename"], "paper.pdf")
            self.assertEqual(mock_vs_inst.search.call_count, 1)
            self.assertEqual(retrieval_cache.stats()["misses"], 1)
            self.assertEqual(retrieval_cache.stats()["hits"], 0)

            # Second retrieval (cache hit)
            res2 = db_retrieve(db=mock_db, user_id="user_a", query="deep learning", top_k=5)
            self.assertEqual(len(res2), 1)
            self.assertEqual(res2[0]["filename"], "paper.pdf")
            # VectorStore search was NOT called again
            self.assertEqual(mock_vs_inst.search.call_count, 1)
            self.assertEqual(retrieval_cache.stats()["hits"], 1)

    def test_retrieve_candidates_bypasses_cache_when_use_cache_false(self):
        """Setting use_cache=False forces fresh retrieval and does not update cache."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.get_eligible_indexed_documents") as mock_get_eligible, \
             patch("backend.services.embedding_service.EmbeddingService.embed_query") as mock_embed, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_get_doc_ids.return_value = [10]
            mock_get_eligible.return_value = [{"id": 10, "index_version": 1}]
            mock_embed.return_value = [0.1, 0.2, 0.3]

            mock_vs_inst = MagicMock()
            mock_vs_inst.search.return_value = {
                "documents": [["Retrieved text chunk"]],
                "metadatas": [[{"document_id": 10, "filename": "paper.pdf", "chunk_index": 0}]],
                "distances": [[0.1]],
            }
            mock_vs_cls.return_value = mock_vs_inst

            res = retrieve_candidates(
                db=mock_db,
                user_id="user_a",
                query="deep learning",
                retrieval_config={"strategy": "dense", "top_k": 5},
                use_cache=False,
            )
            self.assertEqual(len(res), 1)
            self.assertEqual(retrieval_cache.stats()["hits"], 0)
            self.assertEqual(retrieval_cache.stats()["misses"], 0)
            self.assertEqual(retrieval_cache.stats()["entries"], 0)

    def test_reindexing_automatically_invalidates_cached_candidates(self):
        """When a document is reindexed, index_version increments, logically invalidating old candidates."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.get_eligible_indexed_documents") as mock_get_eligible, \
             patch("backend.services.embedding_service.EmbeddingService.embed_query") as mock_embed, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_get_doc_ids.return_value = [10]
            mock_embed.return_value = [0.1, 0.2, 0.3]
            mock_vs_inst = MagicMock()
            mock_vs_cls.return_value = mock_vs_inst

            # Initial version: index_version = 1
            mock_get_eligible.return_value = [{"id": 10, "index_version": 1}]
            mock_vs_inst.search.return_value = {
                "documents": [["Old version content"]],
                "metadatas": [[{"document_id": 10, "filename": "paper.pdf", "chunk_index": 0}]],
                "distances": [[0.1]],
            }

            res1 = db_retrieve(db=mock_db, user_id="user_a", query="neural networks", top_k=5)
            self.assertEqual(res1[0]["text"], "Old version content")
            self.assertEqual(mock_vs_inst.search.call_count, 1)

            # Document is reindexed: index_version becomes 2
            mock_get_eligible.return_value = [{"id": 10, "index_version": 2}]
            mock_vs_inst.search.return_value = {
                "documents": [["Updated version content with new discoveries"]],
                "metadatas": [[{"document_id": 10, "filename": "paper.pdf", "chunk_index": 0}]],
                "distances": [[0.05]],
            }

            # Same query with updated corpus must re-execute retrieval
            res2 = db_retrieve(db=mock_db, user_id="user_a", query="neural networks", top_k=5)
            self.assertEqual(res2[0]["text"], "Updated version content with new discoveries")
            self.assertEqual(mock_vs_inst.search.call_count, 2)
            self.assertEqual(retrieval_cache.stats()["misses"], 2)

    def test_document_deletion_automatically_invalidates_cached_candidates(self):
        """When a document is deleted from DB, eligible list changes, logically invalidating old candidates."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.get_eligible_indexed_documents") as mock_get_eligible, \
             patch("backend.services.embedding_service.EmbeddingService.embed_query") as mock_embed, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_embed.return_value = [0.1, 0.2]
            mock_vs_inst = MagicMock()
            mock_vs_cls.return_value = mock_vs_inst

            # User has docs 1 and 2
            mock_get_doc_ids.return_value = [1, 2]
            mock_get_eligible.return_value = [
                {"id": 1, "index_version": 1},
                {"id": 2, "index_version": 1},
            ]
            mock_vs_inst.search.return_value = {
                "documents": [["Doc 1 text", "Doc 2 text"]],
                "metadatas": [[{"document_id": 1}, {"document_id": 2}]],
                "distances": [[0.1, 0.2]],
            }

            res1 = db_retrieve(db=mock_db, user_id="user_a", query="shared topic", top_k=5)
            self.assertEqual(len(res1), 2)
            self.assertEqual(mock_vs_inst.search.call_count, 1)

            # Doc 2 is deleted: eligible list is now only [1]
            mock_get_doc_ids.return_value = [1]
            mock_get_eligible.return_value = [{"id": 1, "index_version": 1}]
            mock_vs_inst.search.return_value = {
                "documents": [["Doc 1 text"]],
                "metadatas": [[{"document_id": 1}]],
                "distances": [[0.1]],
            }

            res2 = db_retrieve(db=mock_db, user_id="user_a", query="shared topic", top_k=5)
            self.assertEqual(len(res2), 1)
            # Retrieval was re-executed because key changed
            self.assertEqual(mock_vs_inst.search.call_count, 2)

    def test_unauthorized_user_with_no_documents_returns_empty_immediately(self):
        """If user has no indexed documents, retrieval returns empty without querying vector store or cache."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_get_doc_ids.return_value = []

            results = db_retrieve(db=mock_db, user_id="unauthorized_user", query="secret query")
            self.assertEqual(results, [])
            self.assertEqual(mock_vs_cls.call_count, 0)
            self.assertEqual(retrieval_cache.stats()["entries"], 0)

    def test_strict_multi_tenant_isolation(self):
        """User A and User B querying same query receive only their own indexed documents."""
        mock_db = MagicMock()

        with patch("retrieval.get_indexed_document_ids") as mock_get_doc_ids, \
             patch("retrieval.get_eligible_indexed_documents") as mock_get_eligible, \
             patch("backend.services.embedding_service.EmbeddingService.embed_query") as mock_embed, \
             patch("retrieval.VectorStore") as mock_vs_cls:

            mock_embed.return_value = [0.5, 0.5]
            mock_vs_inst = MagicMock()
            mock_vs_cls.return_value = mock_vs_inst

            # User A query
            mock_get_doc_ids.return_value = [100]
            mock_get_eligible.return_value = [{"id": 100, "index_version": 1}]
            mock_vs_inst.search.return_value = {
                "documents": [["User A confidential text"]],
                "metadatas": [[{"document_id": 100, "filename": "user_a.pdf"}]],
                "distances": [[0.1]],
            }
            res_a = db_retrieve(db=mock_db, user_id="user_a", query="confidential search")
            self.assertEqual(res_a[0]["filename"], "user_a.pdf")

            # User B query with identical search text
            mock_get_doc_ids.return_value = [200]
            mock_get_eligible.return_value = [{"id": 200, "index_version": 1}]
            mock_vs_inst.search.return_value = {
                "documents": [["User B separate project"]],
                "metadatas": [[{"document_id": 200, "filename": "user_b.pdf"}]],
                "distances": [[0.2]],
            }
            res_b = db_retrieve(db=mock_db, user_id="user_b", query="confidential search")
            self.assertEqual(res_b[0]["filename"], "user_b.pdf")

            # Both had separate cache entries
            self.assertEqual(retrieval_cache.stats()["entries"], 2)
            self.assertEqual(retrieval_cache.stats()["misses"], 2)


class TestRetrievalBenchmarkExecution(unittest.TestCase):
    """Benchmark execution and report generation validation."""

    def test_run_retrieval_benchmark_produces_valid_report(self):
        """Verify run_retrieval_benchmark measures cache speedup and generates JSON report."""
        test_output = "backend/evaluation/test_retrieval_cache_benchmark.json"
        try:
            report = run_retrieval_benchmark(
                trials=3,
                max_entries=64,
                output_path=test_output,
            )

            self.assertIn("workload", report)
            self.assertIn("cache_disabled", report)
            self.assertIn("cache_enabled", report)
            self.assertIn("performance", report)

            perf = report["performance"]
            self.assertIn("speedup_factor", perf)
            self.assertIn("latency_reduction_percent", perf)
            self.assertIn("retrieval_call_reduction_percent", perf)

            self.assertTrue(os.path.exists(test_output))
            with open(test_output, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["workload"]["trials"], 3)
        finally:
            if os.path.exists(test_output):
                os.remove(test_output)


if __name__ == "__main__":
    unittest.main()
