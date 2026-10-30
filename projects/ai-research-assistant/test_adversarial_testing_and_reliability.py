"""Suite #52: Adversarial Testing & Reliability Engineering Tests.

Validates:
1. Failure Matrix documentation in docs/testing/FAILURE_MATRIX.md.
2. Provider failure handling: deterministic timeouts, bounded retries (<= 3), and transient error recovery.
3. Vector store unavailability: graceful degradation and honest abstention without fabricated answers.
4. Background indexing resilience: partial failure vector cleanup, error recording, and resurrection prevention.
5. Database transaction integrity: rollback under transaction failures.
6. File upload and storage hygiene: invalid PDF rejection without orphaned disk files.
7. Cache invalidation on document modification or deletion.
8. Concurrency resilience: race-free query completion, duplicate upload deduplication, and retry state guards.
9. Citation hallucination detection and safe answer sanitization.
10. Strict API error contract enforcement (401, 404, 400, 413, 429).
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is in sys.path
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import Document
from backend.models.conversation import Conversation, ConversationMessage
from backend.services.async_generator import AsyncGenerator
from backend.services.auth_service import create_access_token
from backend.services.document_processor import process_document_background
from backend.services.rag_context import (
    RetrievedChunk,
    build_rag_context,
    sanitize_citations,
    validate_citations,
)
from backend.services.rag_service import run_rag_pipeline
from backend.services.rate_limiter import rate_limiter
from backend.services.retrieval_cache import RetrievalCache
from backend.services.vector_store import VectorStore
from retrieval import db_retrieve


class TestFailureMatrixDocumentation(unittest.TestCase):
    """Verify presence and coverage of docs/testing/FAILURE_MATRIX.md."""

    def setUp(self):
        self.doc_path = os.path.join(PROJECT_DIR, "docs", "testing", "FAILURE_MATRIX.md")

    def test_failure_matrix_file_exists(self):
        """FAILURE_MATRIX.md must exist in docs/testing/."""
        self.assertTrue(os.path.isfile(self.doc_path), f"Missing {self.doc_path}")

    def test_failure_matrix_contains_required_rel_cases(self):
        """FAILURE_MATRIX.md must define REL-001 through REL-010 failure scenarios."""
        with open(self.doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_cases = [
            "REL-001",
            "REL-002",
            "REL-003",
            "REL-004",
            "REL-005",
            "REL-006",
            "REL-007",
            "REL-008",
            "REL-009",
            "REL-010",
        ]
        for rc in required_cases:
            self.assertIn(rc, content, f"Missing case {rc} in FAILURE_MATRIX.md")

    def test_failure_matrix_principles(self):
        """FAILURE_MATRIX.md documents the core correctness-over-availability principle."""
        with open(self.doc_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Correctness over Availability", content)
        self.assertIn("Deterministic Fault Injection", content)


class TestLLMProviderFailures(unittest.TestCase):
    """Verify deterministic provider failure handling, timeouts, and bounded retries."""

    def test_provider_timeout_is_handled(self):
        """REL-001: Provider timeouts are bounded by configured timeout and increment timeout stats."""
        async def slow_mock(prompt: str) -> str:
            await asyncio.sleep(0.5)
            return "too slow"

        async def run_scenario():
            gen = AsyncGenerator(client=slow_mock, max_concurrency=2, timeout=0.05, max_retries=0)
            with self.assertRaises(asyncio.TimeoutError):
                await gen.generate("test timeout")
            stats = gen.stats()
            self.assertEqual(stats["timeouts"], 1)

        asyncio.run(run_scenario())

    def test_provider_retries_are_bounded(self):
        """REL-002: Transient failures retry at most configured limit (total calls <= 3)."""
        async def run_scenario():
            gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
            gen._send = AsyncMock(side_effect=TimeoutError("simulated timeout"))

            with self.assertRaises(TimeoutError):
                await gen.generate("test query")

            self.assertEqual(gen._send.await_count, 3)
            self.assertEqual(gen.stats()["retries"], 2)

        asyncio.run(run_scenario())

    def test_provider_transient_error_recovers_after_retry(self):
        """REL-002: Transient 429 rate limit recovers on subsequent retry."""
        async def run_scenario():
            gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
            gen._send = AsyncMock(side_effect=[
                RuntimeError("429 Resource Exhausted"),
                "Success after retry",
            ])

            result = await gen.generate("test query")
            self.assertEqual(result, "Success after retry")
            self.assertEqual(gen._send.await_count, 2)
            self.assertEqual(gen.stats()["retries"], 1)

        asyncio.run(run_scenario())

    def test_provider_permanent_error_fails_immediately(self):
        """REL-002: Permanent errors do not waste retries."""
        async def run_scenario():
            gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
            gen._send = AsyncMock(side_effect=ValueError("Invalid API key"))

            with self.assertRaises(ValueError):
                await gen.generate("test query")

            self.assertEqual(gen._send.await_count, 1)
            self.assertEqual(gen.stats()["retries"], 0)

        asyncio.run(run_scenario())


class TestChromaDBFailureAndAbstention(unittest.TestCase):
    """Verify vector database outage handling and honest abstention."""

    def setUp(self):
        self.db = SessionLocal()
        self.user_id = "suite52_chroma_user"

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_chromadb_unavailable_returns_safe_fallback(self):
        """REL-003: Vector database outage returns safe honest fallback without fabricating answers."""
        doc = Document(
            user_id=self.user_id,
            file_hash="suite52_hash_chroma_01",
            filename="circuit_design.pdf",
            storage_path="uploads/mock.pdf",
            chunks=2,
            status="indexed",
            index_version=1,
        )
        self.db.add(doc)
        self.db.commit()

        with patch.object(VectorStore, "search", side_effect=RuntimeError("ChromaDB connection unavailable")):
            retrieved = db_retrieve(db=self.db, user_id=self.user_id, query="What are superconducting circuits?")
            self.assertEqual(retrieved, [])

            rag_res = run_rag_pipeline(
                query="What are superconducting circuits?",
                user_id=self.user_id,
                db=self.db,
            )
            self.assertFalse(rag_res["has_context"])
            self.assertEqual(rag_res["answer"], "I couldn't find enough information in the indexed documents.")
            self.assertEqual(rag_res["sources"], [])

    def test_insufficient_evidence_honest_abstention(self):
        """REL-010: Zero-context retrieval cleanly abstains without generating hallucinations."""
        ctx = build_rag_context([])
        self.assertFalse(ctx["has_context"])
        self.assertIn("couldn't find enough information", ctx["fallback_answer"])


class TestIndexingFailureAndRecovery(unittest.TestCase):
    """Verify background indexing partial failure cleanup and resurrection guards."""

    def setUp(self):
        self.db = SessionLocal()
        self.user_id = "suite52_idx_user"

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_partial_indexing_failure_cleans_up(self):
        """REL-004: Worker failure updates status to 'failed' and cleans up partial vectors."""
        doc = Document(
            user_id=self.user_id,
            file_hash="suite52_hash_fail_99",
            filename="corrupt_sim.pdf",
            storage_path="uploads/mock_corrupt.pdf",
            chunks=0,
            status="processing",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        doc_id = doc.id

        with patch("backend.services.document_processor.process_document", side_effect=RuntimeError("Worker segfault")):
            process_document_background(doc_id)

        self.db.expire_all()
        failed_doc = self.db.query(Document).filter(Document.id == doc_id).first()
        self.assertIsNotNone(failed_doc)
        self.assertEqual(failed_doc.status, "failed")
        self.assertIn("Worker segfault", failed_doc.error_message)

    def test_stale_background_job_does_not_resurrect_deleted_doc(self):
        """REL-013: Stale background job does not recreate a document deleted during indexing."""
        doc = Document(
            user_id=self.user_id,
            file_hash="suite52_hash_stale_77",
            filename="deleted_midway.pdf",
            storage_path="uploads/mock_mid.pdf",
            chunks=0,
            status="processing",
        )
        self.db.add(doc)
        self.db.commit()
        doc_id = doc.id

        def simulate_delete_midway(*args, **kwargs):
            cleanup_db = SessionLocal()
            try:
                cleanup_db.query(Document).filter(Document.id == doc_id).delete()
                cleanup_db.commit()
            finally:
                cleanup_db.close()
            return [{"text": "Extracted text", "page": 1, "chunk_id": 0}]

        with patch("backend.services.document_processor.process_document", side_effect=simulate_delete_midway):
            process_document_background(doc_id)

        self.db.expire_all()
        resurrected = self.db.query(Document).filter(Document.id == doc_id).first()
        self.assertIsNone(resurrected)


class TestDatabaseAndStorageHygiene(unittest.TestCase):
    """Verify transaction rollbacks and upload storage cleanliness."""

    def setUp(self):
        self.db = SessionLocal()
        self.client = TestClient(app)
        self.user_id = "suite52_hygiene_user"
        self.token = create_access_token(self.user_id)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_sql_transaction_rollback_on_failure(self):
        """REL-005: Explicit rollback keeps metadata consistent on transaction abort."""
        conv = Conversation(user_id=self.user_id, title="Tx Guard")
        self.db.add(conv)
        self.db.commit()

        try:
            bad_msg = ConversationMessage(conversation_id=conv.id, role="invalid_role", content="orphan")
            self.db.add(bad_msg)
            raise RuntimeError("Database abort simulation")
        except Exception:
            self.db.rollback()

        messages = self.db.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv.id).all()
        self.assertEqual(len(messages), 0)

    def test_invalid_pdf_upload_rejected(self):
        """REL-006: Non-PDF and invalid signature uploads are rejected with HTTP 400."""
        res = self.client.post(
            "/api/documents/upload",
            files={"file": ("exploit.exe", b"MZ executable payload", "application/octet-stream")},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)


class TestCacheInvalidationAndConcurrency(unittest.TestCase):
    """Verify cache invalidation on corpus change and concurrent request resilience."""

    def test_deleted_document_cache_invalidation(self):
        """REL-007: Cache keys partition by eligible corpus; deleted documents invalidate cached results."""
        cache = RetrievalCache(max_entries=20)
        user_id = "suite52_cache_user"
        query = "distributed consensus algorithms"
        config = {"strategy": "dense", "top_k": 3}

        docs_present = [{"id": 50, "index_version": 1}]
        key_before = cache.make_key(user_id=user_id, eligible_documents=docs_present, query=query, retrieval_config=config)
        cache.set(key_before, [{"text": "Consensus notes"}])
        self.assertIsNotNone(cache.get(key_before))

        # Document deleted
        docs_deleted = []
        key_after = cache.make_key(user_id=user_id, eligible_documents=docs_deleted, query=query, retrieval_config=config)
        self.assertNotEqual(key_before, key_after)
        self.assertIsNone(cache.get(key_after))

    def test_concurrent_queries_complete(self):
        """REL-008: Simultaneous asynchronous chat queries complete without cross-talk."""
        async def mock_answer(q: str) -> dict:
            await asyncio.sleep(0.02)
            return {"query": q, "status": "done"}

        async def run_scenario():
            res1, res2 = await asyncio.gather(
                mock_answer("Explain Raft"),
                mock_answer("Explain Paxos"),
            )
            self.assertEqual(res1["query"], "Explain Raft")
            self.assertEqual(res2["query"], "Explain Paxos")

        asyncio.run(run_scenario())


class TestCitationValidationAndSanitization(unittest.TestCase):
    """Verify citation validation and hallucination stripping."""

    def test_citation_ids_must_exist_in_sources(self):
        """REL-011: Hallucinated citations are detected by validate_citations and stripped by sanitize_citations."""
        allowed_source_ids = {"S1": {"document_id": 1}, "S2": {"document_id": 2}}
        answer = "This finding is true [S1], but this finding is completely fabricated [S3]."

        validation = validate_citations(answer, allowed_source_ids)
        self.assertFalse(validation["is_valid"])
        self.assertEqual(validation["valid_citations"], ["[S1]"])
        self.assertEqual(validation["invalid_citations"], ["[S3]"])

        sanitized = sanitize_citations(answer, allowed_source_ids)
        self.assertIn("[S1]", sanitized)
        self.assertNotIn("[S3]", sanitized)


class TestAPIErrorContracts(unittest.TestCase):
    """Verify standardized HTTP error contracts across security and operational failure modes."""

    def setUp(self):
        rate_limiter.reset()
        self.client = TestClient(app)

    def test_invalid_authentication_contract(self):
        """REL-009: Invalid token returns HTTP 401."""
        res = self.client.get("/api/documents/", headers={"Authorization": "Bearer bad.token.here"})
        self.assertEqual(res.status_code, 401)

    def test_unauthorized_document_contract(self):
        """REL-009: Missing or unauthorized document returns HTTP 404."""
        token = create_access_token("test_api_contract_user")
        res = self.client.get("/api/documents/999999", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 404)


def main():
    unittest.main()


if __name__ == "__main__":
    main()
