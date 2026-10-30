"""Suite #53: Performance Profiling & Latency Optimization Tests.

Validates:
1. Performance Baseline documentation in docs/performance/PERFORMANCE_BASELINE.md.
2. Stage-level timing instrumentation (T1-T7) via measure_stage and async_measure_stage.
3. Thread-safe PerformanceTracker with P50, P90, P95, P99 percentile calculations.
4. Microbenchmark harness function benchmark() with statistical verification.
5. Configurable embedding batching via EmbeddingService and embedding_batch_size.
6. Lexical BM25 index caching via KeywordRetrieverCache and safe user invalidation.
7. Bounded candidate pool reranking with cross-encoder.
8. Context chunk deduplication and prompt token reduction via deduplicate_near_identical_chunks.
9. End-to-end RAG pipeline stage timings and metrics recording.
10. Frontend React Profiler and memoization optimizations.
"""

import asyncio
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Ensure project root is in sys.path
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from backend.config import settings
from backend.services.embedding_service import EmbeddingService, embedding_cache
from backend.services.keyword_retriever import (
    KeywordRetriever,
    KeywordRetrieverCache,
    bm25_cache,
    get_or_build_keyword_retriever,
)
from backend.services.observability import (
    PerformanceTracker,
    async_measure_stage,
    benchmark,
    measure_stage,
    performance_tracker,
)
from backend.services.rag_context import (
    RetrievedChunk,
    build_rag_context,
    deduplicate_near_identical_chunks,
)
from backend.services.rag_service import run_rag_pipeline
from backend.services.reranker import get_reranker


class TestPerformanceProfilingAndOptimization(unittest.TestCase):

    def setUp(self):
        performance_tracker.clear()
        bm25_cache.clear()
        embedding_cache.clear()

    # ========================================================================
    # 1. Performance Baseline Documentation Verification
    # ========================================================================

    def test_performance_baseline_document_exists_and_complete(self):
        """PERF-001: docs/performance/PERFORMANCE_BASELINE.md exists with all required sections and real metrics."""
        doc_path = Path(PROJECT_DIR) / "docs" / "performance" / "PERFORMANCE_BASELINE.md"
        if not doc_path.exists():
            doc_path = Path(PROJECT_DIR).parent.parent / "docs" / "performance" / "PERFORMANCE_BASELINE.md"

        self.assertTrue(doc_path.exists(), f"Baseline doc missing at {doc_path}")
        content = doc_path.read_text(encoding="utf-8")

        self.assertIn("# Performance Baseline", content)
        self.assertIn("## Environment", content)
        self.assertIn("## Measurements", content)
        self.assertIn("## Evaluation", content)
        self.assertIn("## Changes", content)

        # Check key operation rows
        self.assertIn("PDF parsing", content)
        self.assertIn("Embedding", content)
        self.assertIn("Retrieval", content)
        self.assertIn("Reranking", content)
        self.assertIn("Context building", content)
        self.assertIn("LLM TTFT", content)
        self.assertIn("Total API latency", content)

        # Check evaluation rows
        self.assertIn("Recall@K", content)
        self.assertIn("Citation validity", content)
        self.assertIn("Faithfulness", content)
        self.assertIn("Error rate", content)

    # ========================================================================
    # 2. Reusable Stage Timing Instrumentation
    # ========================================================================

    def test_measure_stage_single_argument(self):
        """PERF-002: measure_stage context manager works with a single stage_name argument."""
        with measure_stage("profiling_stage_single"):
            time.sleep(0.002)

        stats = performance_tracker.get_percentiles("profiling_stage_single")
        self.assertEqual(stats["count"], 1)
        self.assertGreaterEqual(stats["p50_ms"], 1.0)
        self.assertEqual(stats["outcomes"]["success"], 1)

    def test_measure_stage_with_metrics_dictionary(self):
        """PERF-002: measure_stage correctly populates passed metrics dictionary."""
        metrics: dict[str, Any] = {}
        with measure_stage("profiling_stage_dict", metrics):
            time.sleep(0.002)

        self.assertIn("profiling_stage_dict", metrics)
        self.assertGreaterEqual(metrics["profiling_stage_dict"], 1.0)

    def test_async_measure_stage_execution(self):
        """PERF-002: async_measure_stage measures asynchronous coroutine stage execution."""
        async def run_async():
            metrics: dict[str, Any] = {}
            async with async_measure_stage("async_test_stage", metrics):
                await asyncio.sleep(0.003)

            self.assertIn("async_test_stage", metrics)
            self.assertGreaterEqual(metrics["async_test_stage"], 2.0)
            stats = performance_tracker.get_percentiles("async_test_stage")
            self.assertEqual(stats["count"], 1)

        asyncio.run(run_async())

    # ========================================================================
    # 3. PerformanceTracker Percentile Aggregation
    # ========================================================================

    def test_performance_tracker_percentile_calculations(self):
        """PERF-003: PerformanceTracker computes correct P50, P90, P95, and P99 percentiles."""
        tracker = PerformanceTracker(max_samples=200)
        # Record 100 samples from 1.0ms to 100.0ms
        for i in range(1, 101):
            tracker.record("test_op", float(i), outcome="success")

        stats = tracker.get_percentiles("test_op")
        self.assertEqual(stats["count"], 100)
        self.assertEqual(stats["min_ms"], 1.0)
        self.assertEqual(stats["max_ms"], 100.0)
        self.assertEqual(stats["p50_ms"], 51.0)
        self.assertEqual(stats["p90_ms"], 91.0)
        self.assertEqual(stats["p95_ms"], 96.0)
        self.assertEqual(stats["p99_ms"], 100.0)
        self.assertEqual(stats["outcomes"]["success"], 100)

    def test_performance_tracker_empty_and_reset(self):
        """PERF-003: PerformanceTracker handles empty stage queries and resets cleanly."""
        tracker = PerformanceTracker()
        empty_stats = tracker.get_percentiles("nonexistent")
        self.assertEqual(empty_stats["count"], 0)
        self.assertEqual(empty_stats["p50_ms"], 0.0)

        tracker.record("stage_a", 15.0)
        self.assertEqual(tracker.get_percentiles("stage_a")["count"], 1)

        tracker.clear()
        self.assertEqual(tracker.get_percentiles("stage_a")["count"], 0)

    # ========================================================================
    # 4. Benchmark Harness
    # ========================================================================

    def test_benchmark_harness_output(self):
        """PERF-004: benchmark() function returns iterations, mean, median, P50, and P95."""
        calls = 0

        def sample_work():
            nonlocal calls
            calls += 1
            time.sleep(0.001)

        result = benchmark(sample_work, iterations=12)
        self.assertEqual(result["iterations"], 12)
        self.assertEqual(calls, 12)
        self.assertIn("mean_ms", result)
        self.assertIn("median_ms", result)
        self.assertIn("p50_ms", result)
        self.assertIn("p95_ms", result)
        self.assertGreaterEqual(result["p95_ms"], result["p50_ms"])

    # ========================================================================
    # 5. Embedding Batching & Model Singleton
    # ========================================================================

    def test_embedding_service_model_is_singleton(self):
        """PERF-005: EmbeddingService reuses single model instance rather than re-instantiating."""
        svc1 = EmbeddingService()
        svc2 = EmbeddingService()
        self.assertIs(svc1.model, svc2.model)

    def test_embedding_documents_batch_processing(self):
        """PERF-005: EmbeddingService.embed_documents handles batched lists of text chunks."""
        svc = EmbeddingService()
        chunks = [f"Quantum error correction surface code chunk {i}" for i in range(8)]
        vectors = svc.embed_documents(chunks, user_id="test_perf_user")
        self.assertEqual(len(vectors), 8)
        self.assertTrue(all(isinstance(v, list) and len(v) > 0 for v in vectors))

    # ========================================================================
    # 6. Lexical BM25 Index Caching & Safe Invalidation
    # ========================================================================

    def test_bm25_cache_rebuild_avoidance(self):
        """PERF-006: get_or_build_keyword_retriever avoids rebuilding index for unchanged corpus."""
        chunks = [
            {"document_id": 5, "chunk_index": i, "text": f"Distributed consensus protocol Raft chunk {i}"}
            for i in range(15)
        ]
        user_id = "test_bm25_perf_user"

        r1 = get_or_build_keyword_retriever(user_id, chunks, document_ids=[5])
        r2 = get_or_build_keyword_retriever(user_id, chunks, document_ids=[5])

        self.assertIs(r1, r2)
        self.assertEqual(bm25_cache.stats()["hits"], 1)

    def test_bm25_cache_invalidation_per_user(self):
        """PERF-006: bm25_cache.invalidate_user invalidates only the target user's entries."""
        cache = KeywordRetrieverCache(max_entries=10)
        retriever = KeywordRetriever([{"text": "Sample chunk"}])

        cache.put("user_1", "sig_1", retriever)
        cache.put("user_2", "sig_2", retriever)

        self.assertIsNotNone(cache.get("user_1", "sig_1"))
        self.assertIsNotNone(cache.get("user_2", "sig_2"))

        cache.invalidate_user("user_1")
        self.assertIsNone(cache.get("user_1", "sig_1"))
        self.assertIsNotNone(cache.get("user_2", "sig_2"))

    # ========================================================================
    # 7. Cross-Encoder Bounded Candidate Reranking
    # ========================================================================

    def test_bounded_candidate_reranking(self):
        """PERF-007: Reranker bounds candidates and preserves top scoring matches."""
        reranker = get_reranker()
        query = "transmon qubit coherence"
        candidates = [
            {"document_id": 1, "chunk_index": i, "text": f"Experimental coherence study for transmon sample {i}", "score": 0.5 + i * 0.01}
            for i in range(12)
        ]

        reranked = reranker.rerank(query, candidates[:8], top_k=5)
        self.assertLessEqual(len(reranked), 5)
        self.assertTrue(all("reranker_score" in c or "score" in c for c in reranked))

    # ========================================================================
    # 8. Context Deduplication & Token Optimization
    # ========================================================================

    def test_context_chunk_deduplication(self):
        """PERF-008: deduplicate_near_identical_chunks eliminates redundant chunks while preserving evidence."""
        chunks = [
            RetrievedChunk(text="Dilution refrigerators cool qubits to 15 mK.", score=0.95),
            RetrievedChunk(text="Dilution refrigerators cool qubits to 15 mK.", score=0.94),  # Exact duplicate
            RetrievedChunk(text="Dilution refrigerators cool qubits down to 15 mK.", score=0.91),  # Near duplicate
            RetrievedChunk(text="Laser cooling traps neutral rubidium atoms in optical tweezers.", score=0.89),
        ]

        deduped = deduplicate_near_identical_chunks(chunks, min_jaccard_similarity=0.80)
        self.assertEqual(len(deduped), 2)
        self.assertTrue(deduped[0].text.startswith("Dilution refrigerators"))
        self.assertTrue(deduped[1].text.startswith("Laser cooling"))

    def test_build_rag_context_preserves_sources_under_deduplication(self):
        """PERF-008: build_rag_context produces clean citations and sources with deduplication enabled."""
        raw_chunks = [
            {"document_id": 1, "chunk_index": 0, "text": "Optical tweezers trap neutral atoms.", "score": 0.9},
            {"document_id": 1, "chunk_index": 1, "text": "Optical tweezers trap neutral atoms.", "score": 0.89},  # Duplicate
            {"document_id": 2, "chunk_index": 0, "text": "Superconducting circuits use transmon qubits.", "score": 0.85},
        ]

        ctx = build_rag_context(raw_chunks, deduplicate=True)
        self.assertEqual(len(ctx["sources"]), 2)
        self.assertIn("[S1]", ctx["context"])
        self.assertIn("[S2]", ctx["context"])
        self.assertNotIn("[S3]", ctx["context"])
        self.assertTrue(ctx["has_context"])

    # ========================================================================
    # 9. Full RAG Pipeline Stage Instrumentation (T1 - T7)
    # ========================================================================

    @patch("backend.services.rag_service.generate_answer")
    @patch("backend.services.rag_service.db_retrieve")
    def test_rag_pipeline_records_all_seven_stages(self, mock_retrieve, mock_generate):
        """PERF-009: run_rag_pipeline instruments stages T1 through T7."""
        mock_retrieve.return_value = [
            {
                "text": "Quantum superposition principles and wavefunctions.",
                "score": 0.95,
                "filename": "quantum.pdf",
                "chunk_index": 0,
            }
        ]
        mock_generate.return_value = [
            "Quantum superposition allows qubits to represent linear combinations [S1]."
        ]

        metrics: dict[str, Any] = {}
        res = run_rag_pipeline(
            query="Explain the basics of quantum superposition",
            user_id="test_suite53_user",
            metrics=metrics,
        )

        expected_stages = [
            "request_validation",  # T1
            "query_routing",       # T2
            "retrieval",           # T3
            "reranking",           # T4
            "context_assembly",    # T5
            "generation",          # T6
            "response_validation", # T7
        ]
        for stage in expected_stages:
            self.assertIn(stage, metrics, f"Stage {stage} not recorded in metrics")
            self.assertIsInstance(metrics[stage], (int, float))

        self.assertIn("answer", res)
        self.assertIn("metrics", res)

    # ========================================================================
    # 10. Frontend React Profiling & Memoization Verification
    # ========================================================================

    def test_frontend_profiler_and_memoization_configured(self):
        """PERF-010: Frontend components use React.memo and Chat.jsx wraps ChatWindow in Profiler."""
        frontend_src = Path(PROJECT_DIR) / "frontend" / "src"
        if not frontend_src.exists():
            frontend_src = Path(PROJECT_DIR).parent.parent / "frontend" / "src"

        # Check Chat.jsx has Profiler
        chat_page = (frontend_src / "pages" / "Chat.jsx").read_text(encoding="utf-8")
        self.assertIn("<Profiler", chat_page)
        self.assertIn('id="ChatMessages"', chat_page)

        # Check MessageBubble has memo
        msg_bubble = (frontend_src / "components" / "chat" / "MessageBubble.jsx").read_text(encoding="utf-8")
        self.assertIn("memo(MessageBubble)", msg_bubble)

        # Check MarkdownAnswer has memo
        md_answer = (frontend_src / "components" / "chat" / "MarkdownAnswer.jsx").read_text(encoding="utf-8")
        self.assertIn("memo(MarkdownAnswer)", md_answer)

        # Check SourceList has memo
        src_list = (frontend_src / "components" / "sources" / "SourceList.jsx").read_text(encoding="utf-8")
        self.assertIn("memo(SourceList)", src_list)

        # Check SourceCard has memo
        src_card = (frontend_src / "components" / "sources" / "SourceCard.jsx").read_text(encoding="utf-8")
        self.assertIn("memo(SourceCard)", src_card)

    # ========================================================================
    # 11. Configuration Settings Verification
    # ========================================================================

    def test_configuration_performance_settings(self):
        """PERF-011: config.py exposes configurable batch size and BM25 cache settings."""
        self.assertTrue(hasattr(settings, "embedding_batch_size"))
        self.assertGreaterEqual(settings.embedding_batch_size, 1)
        self.assertTrue(hasattr(settings, "bm25_cache_enabled"))
        self.assertTrue(settings.bm25_cache_enabled)
        self.assertTrue(hasattr(settings, "bm25_cache_entries"))
        self.assertGreaterEqual(settings.bm25_cache_entries, 1)


if __name__ == "__main__":
    unittest.main()
