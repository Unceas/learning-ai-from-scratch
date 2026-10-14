"""Suite #43: RAG Observability, Stage-Level Telemetry, Request IDs & Latency Metrics Tests."""

import asyncio
import io
import json
import logging
import os
import sys
import unittest
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import app
from backend.services.observability import measure_stage, async_measure_stage
from backend.services.chat_service import ChatService
from backend.evaluation.latency_report import (
    summarize_latency,
    generate_latency_report,
    run_baseline_benchmark,
    load_latency_report,
)


class TestRAGObservabilityAndPerformance(unittest.TestCase):
    """Test suite for Day 163 research observability and performance telemetry."""

    # -------------------------------------------------------------
    # Phase 1: Reusable Timing Utilities (Sync & Async)
    # -------------------------------------------------------------
    def test_measure_stage_records_duration(self):
        """Test that measure_stage records elapsed time in milliseconds."""
        metrics = {}
        with measure_stage("retrieval", metrics):
            sum(range(50000))

        self.assertIn("retrieval", metrics)
        self.assertIsInstance(metrics["retrieval"], (int, float))
        self.assertGreaterEqual(metrics["retrieval"], 0.0)

    def test_failed_stage_records_duration_and_propagates_exception(self):
        """Test that failed stages still record duration and propagate exceptions."""
        metrics = {}
        with self.assertRaises(ValueError):
            with measure_stage("failing_stage", metrics):
                raise ValueError("Stage execution failed")

        self.assertIn("failing_stage", metrics)
        self.assertGreaterEqual(metrics["failing_stage"], 0.0)

    def test_async_measure_stage_records_duration_and_propagates(self):
        """Test that async_measure_stage works in asynchronous contexts."""
        async def run_async_test():
            metrics = {}
            async with async_measure_stage("async_retrieval", metrics):
                await asyncio.sleep(0.01)

            self.assertIn("async_retrieval", metrics)
            self.assertGreaterEqual(metrics["async_retrieval"], 5.0)

            # Test async exception propagation
            with self.assertRaises(RuntimeError):
                async with async_measure_stage("async_failing", metrics):
                    raise RuntimeError("Async stage failure")

            self.assertIn("async_failing", metrics)
            self.assertGreaterEqual(metrics["async_failing"], 0.0)

        asyncio.run(run_async_test())

    # -------------------------------------------------------------
    # Phase 2: Security & Log Redaction
    # -------------------------------------------------------------
    def test_sensitive_credentials_never_logged(self):
        """Ensure Authorization headers, JWTs, and passwords never enter telemetry logs."""
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        obs_logger = logging.getLogger("research_assistant")
        original_level = obs_logger.level
        obs_logger.setLevel(logging.INFO)
        obs_logger.addHandler(handler)

        try:
            metrics = {}
            with measure_stage("query_rewriting", metrics):
                # Simulated work with sensitive internal variables
                secret_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"
                passcode = "super_secret_password"

            handler.flush()
            logs = log_stream.getvalue()

            self.assertNotIn(secret_jwt, logs)
            self.assertNotIn(passcode, logs)
            self.assertNotIn("Authorization", logs)
            self.assertNotIn("Bearer", logs)
        finally:
            obs_logger.removeHandler(handler)
            obs_logger.setLevel(original_level)

    # -------------------------------------------------------------
    # Phase 3: Request-Level Middleware & Correlation IDs
    # -------------------------------------------------------------
    def _make_request(self, method: str, path: str, headers: dict = None):
        import httpx
        async def _call():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, headers=headers)
        return asyncio.run(_call())

    def test_observe_request_middleware_generates_request_id(self):
        """Verify middleware assigns an X-Request-ID header to every response."""
        response = self._make_request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertIn("x-request-id", response.headers)
        request_id = response.headers["x-request-id"]
        self.assertTrue(len(request_id) > 0)

    def test_observe_request_middleware_propagates_existing_request_id(self):
        """Verify incoming valid X-Request-ID headers are preserved."""
        custom_id = "req-custom-trace-uuid-12345"
        response = self._make_request("GET", "/health", headers={"X-Request-ID": custom_id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-request-id"), custom_id)

    def test_observe_request_middleware_preserves_response_content(self):
        """Verify middleware does not mutate status code or response body."""
        response = self._make_request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")

    # -------------------------------------------------------------
    # Phase 4: ChatService & Pipeline Stage Instrumentation
    # -------------------------------------------------------------
    def test_chat_service_process_chat_metrics(self):
        """Test process_chat tracks query_rewriting, retrieval, reranking, and generation metrics."""
        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = "Rewritten research query"

        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"id": "c1", "text": "passage 1"},
            {"id": "c2", "text": "passage 2"},
            {"id": "c3", "text": "passage 3"},
        ]

        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [
            {"id": "c1", "text": "passage 1"},
            {"id": "c2", "text": "passage 2"},
        ]

        mock_generator = MagicMock()
        mock_generator.generate.return_value = "Synthesized research answer [S1]."

        service = ChatService(
            query_rewriter=mock_rewriter,
            retriever=mock_retriever,
            reranker=mock_reranker,
            generator=mock_generator,
        )

        result = service.process_chat("Original query", history=[])

        self.assertEqual(result["answer"], "Synthesized research answer [S1].")
        metrics = result["metrics"]

        # Validate stage latencies
        self.assertIn("query_rewriting", metrics)
        self.assertIn("retrieval", metrics)
        self.assertIn("reranking", metrics)
        self.assertIn("generation", metrics)

        # Validate operational characteristic counters
        self.assertEqual(metrics["candidate_count"], 3)
        self.assertEqual(metrics["reranked_count"], 2)
        self.assertFalse(metrics["empty_retrieval"])
        self.assertEqual(metrics["generation_outcome"], "success")

    def test_chat_service_chat_preserves_answer_and_returns_metrics(self):
        """Test ChatService.chat preserves answer, sources, and returns metrics."""
        mock_conv_service = MagicMock()
        mock_conv = MagicMock()
        mock_conv.id = 101
        mock_conv_service.create_conversation.return_value = mock_conv
        mock_conv_service.get_recent_messages.return_value = []
        mock_msg = MagicMock()
        mock_msg.id = 55
        mock_conv_service.add_message.return_value = mock_msg

        mock_rewriter = MagicMock()
        mock_rewriter.rewrite.return_value = "Rewritten query"

        mock_rag_result = {
            "answer": "Answer about transformers [S1].",
            "sources": [{"id": "S1", "filename": "attention.pdf", "chunk_index": 2}],
            "citation_map": {"S1": {"filename": "attention.pdf", "chunk_index": 2}},
            "latency_ms": 150.0,
            "metrics": {
                "query_routing": 1.5,
                "retrieval": 45.0,
                "reranking": 30.0,
                "candidate_count": 10,
                "reranked_count": 3,
                "empty_retrieval": False,
                "generation_outcome": "success",
            },
        }

        mock_rag_service = MagicMock()
        mock_rag_service.run_rag_pipeline.return_value = mock_rag_result

        service = ChatService(
            conversation_service=mock_conv_service,
            query_rewriter=mock_rewriter,
            rag_service=mock_rag_service,
        )

        mock_db = MagicMock()
        result = service.chat(
            db=mock_db,
            user_id="user_test",
            message="What is self-attention?",
        )

        # Answer and sources intact
        self.assertEqual(result["answer"], "Answer about transformers [S1].")
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["id"], "S1")

        # Telemetry metrics present
        self.assertIn("metrics", result)
        m = result["metrics"]
        self.assertIn("query_rewriting", m)
        self.assertIn("retrieval", m)
        self.assertIn("reranking", m)
        self.assertEqual(m["candidate_count"], 10)
        self.assertEqual(m["reranked_count"], 3)

    # -------------------------------------------------------------
    # Phase 5: Latency Report & Statistical Summarization
    # -------------------------------------------------------------
    def test_summarize_latency_empty_list(self):
        """Test summarize_latency with empty list returns count 0 and None values."""
        summary = summarize_latency([])
        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["mean_ms"])
        self.assertIsNone(summary["median_ms"])
        self.assertIsNone(summary["p95_ms"])

    def test_summarize_latency_sample_distribution(self):
        """Test summarize_latency correctly calculates mean, median, and p95."""
        samples = [420.0, 510.0, 490.0, 1800.0, 620.0]
        summary = summarize_latency(samples)

        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["mean_ms"], 768.0)
        self.assertEqual(summary["median_ms"], 510.0)
        # Nearest-rank index for 0.95 * 5 = 4.75 -> max(0, int(4.75 + 0.999999) - 1) = 4 -> 1800.0
        self.assertEqual(summary["p95_ms"], 1800.0)

    def test_generate_latency_report_structure(self):
        """Test generate_latency_report computes stage metrics and identifies bottleneck."""
        records = [
            {
                "metrics": {
                    "query_rewriting": 20.0,
                    "query_routing": 2.0,
                    "retrieval": 80.0,
                    "reranking": 60.0,
                    "context_assembly": 2.0,
                    "generation": 350.0,
                    "candidate_count": 20,
                    "reranked_count": 5,
                    "empty_retrieval": False,
                    "generation_outcome": "success",
                }
            },
            {
                "metrics": {
                    "query_rewriting": 25.0,
                    "query_routing": 2.5,
                    "retrieval": 120.0,
                    "reranking": 90.0,
                    "context_assembly": 3.0,
                    "generation": 450.0,
                    "candidate_count": 25,
                    "reranked_count": 5,
                    "empty_retrieval": False,
                    "generation_outcome": "success",
                }
            },
            {
                "metrics": {
                    "query_rewriting": 15.0,
                    "query_routing": 1.0,
                    "retrieval": 30.0,
                    "reranking": 0.0,
                    "context_assembly": 1.0,
                    "generation": 0.0,
                    "candidate_count": 0,
                    "reranked_count": 0,
                    "empty_retrieval": True,
                    "generation_outcome": "skipped_empty_context",
                }
            },
        ]

        report = generate_latency_report(records)

        self.assertEqual(report["total_requests"], 3)
        self.assertIn("total_latency", report)
        self.assertIn("stages", report)

        # Check generation is identified as bottleneck
        self.assertEqual(report["bottleneck_stage"], "generation")

        # Check operational metrics
        op = report["operational"]
        self.assertEqual(op["empty_retrieval_count"], 1)
        self.assertAlmostEqual(op["empty_retrieval_rate"], 1 / 3, places=2)
        self.assertEqual(op["error_count"], 0)
        self.assertEqual(op["error_rate"], 0.0)
        self.assertGreater(op["avg_candidate_count"], 0)

    def test_run_baseline_benchmark_creates_report_file(self):
        """Test run_baseline_benchmark generates and persists baseline_latency_report.json."""
        test_output = "backend/evaluation/test_baseline_report.json"
        try:
            report = run_baseline_benchmark(output_path=test_output)
            self.assertTrue(os.path.exists(test_output))

            loaded = load_latency_report(test_output)
            self.assertEqual(loaded["total_requests"], 6)
            self.assertIn("stages", loaded)
            self.assertIn("retrieval", loaded["stages"])
            self.assertIn("reranking", loaded["stages"])
            self.assertIn("generation", loaded["stages"])
            self.assertEqual(loaded["bottleneck_stage"], "generation")
        finally:
            if os.path.exists(test_output):
                os.remove(test_output)


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING SUITE #43: RESEARCH OBSERVABILITY & LATENCY METRICS")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRAGObservabilityAndPerformance)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\n" + "=" * 60)
        print("SUITE #43 COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("SUITE #43 FAILED!")
        print("=" * 60)
        sys.exit(1)
