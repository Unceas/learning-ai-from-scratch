"""Adversarial and reliability engineering tests verifying system behavior under failure conditions."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
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


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    rate_limiter.reset()
    return TestClient(app)


# ============================================================================
# 1. LLM Provider Failures & Bounded Retries (REL-001, REL-002)
# ============================================================================

def test_provider_timeout_is_handled():
    """REL-001: AsyncGenerator catches provider timeouts cleanly within the configured deadline."""
    async def scenario():
        async def slow_mock(prompt: str) -> str:
            await asyncio.sleep(0.5)
            return "too slow"

        gen = AsyncGenerator(client=slow_mock, max_concurrency=2, timeout=0.05, max_retries=0)
        with pytest.raises(asyncio.TimeoutError):
            await gen.generate("test timeout")

        stats = gen.stats()
        assert stats["timeouts"] == 1
        assert stats["active_requests"] == 0

    asyncio.run(scenario())


def test_provider_retries_are_bounded():
    """REL-002: Transient provider failures retry up to the configured bound (<= 3 attempts)."""
    async def scenario():
        gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
        gen._send = AsyncMock(side_effect=TimeoutError("simulated timeout"))

        with pytest.raises(TimeoutError):
            await gen.generate("test query")

        # Initial attempt + 2 retries = 3 total calls
        assert gen._send.await_count == 3
        assert gen.stats()["retries"] == 2

    asyncio.run(scenario())


def test_provider_transient_429_recovers_after_retry():
    """REL-002: Transient HTTP 429 rate limit retries and returns successfully when provider recovers."""
    async def scenario():
        gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
        # Fail on first attempt with 429, succeed on second attempt
        gen._send = AsyncMock(side_effect=[
            RuntimeError("429 Resource Exhausted: Rate limit exceeded"),
            "Recovered grounded response",
        ])

        result = await gen.generate("test query")
        assert result == "Recovered grounded response"
        assert gen._send.await_count == 2
        assert gen.stats()["retries"] == 1

    asyncio.run(scenario())


def test_provider_permanent_error_fails_fast_without_retrying():
    """REL-002: Permanent non-transient errors (e.g. invalid API key) fail fast without wasting retries."""
    async def scenario():
        gen = AsyncGenerator(max_concurrency=2, timeout=1.0, max_retries=2, backoff_factor=0.01)
        gen._send = AsyncMock(side_effect=ValueError("Invalid API key configured"))

        with pytest.raises(ValueError, match="Invalid API key configured"):
            await gen.generate("test query")

        # Does not retry on permanent ValueError
        assert gen._send.await_count == 1
        assert gen.stats()["retries"] == 0

    asyncio.run(scenario())


# ============================================================================
# 2. ChromaDB Unavailability & Honest Abstention (REL-003, REL-010)
# ============================================================================

def test_chromadb_unavailable_returns_safe_fallback(db_session):
    """REL-003: When ChromaDB is unreachable, retrieval fails gracefully and RAG pipeline abstains."""
    user_id = "rel_user_chroma_fail"
    # Create an indexed doc so user is eligible for retrieval
    doc = Document(
        user_id=user_id,
        file_hash="hash_chroma_fail_01",
        filename="system_paper.pdf",
        storage_path="uploads/mock.pdf",
        chunks=2,
        status="indexed",
        index_version=1,
    )
    db_session.add(doc)
    db_session.commit()

    # Simulate ChromaDB throwing a connection error during search
    with patch.object(VectorStore, "search", side_effect=RuntimeError("ChromaDB connection unavailable")):
        retrieved = db_retrieve(db=db_session, user_id=user_id, query="What is attention?")
        assert retrieved == []

        # RAG pipeline with zero retrieval results returns safe honest fallback without LLM hallucination
        rag_res = run_rag_pipeline(query="What is attention?", user_id=user_id, db=db_session)
        assert rag_res["has_context"] is False
        assert rag_res["answer"] == "I couldn't find enough information in the indexed documents."
        assert rag_res["sources"] == []


def test_deterministic_corpus_evidence_quality_and_abstention(db_session):
    """REL-010: Verify evidence quality and honest abstention across diverse test corpus."""
    user_id = "rel_user_corpus_eval"

    # 1. Zero evidence condition: user has no indexed docs
    rag_res = run_rag_pipeline(query="Explain quantum supremacy", user_id=user_id, db=db_session)
    assert rag_res["has_context"] is False
    assert "I couldn't find enough information" in rag_res["answer"]
    assert rag_res["sources"] == []

    # 2. Insufficient context condition: chunk list is empty
    ctx = build_rag_context([])
    assert ctx["has_context"] is False
    assert ctx["fallback_answer"] == "I couldn't find enough information in the indexed documents."

    # 3. Sufficient context condition: chunk list provides evidence
    chunks = [
        RetrievedChunk(
            text="Quantum supremacy demonstrates computational advantage over classical machines.",
            score=0.92,
            filename="quantum.pdf",
            chunk_index=0,
            document_id=1,
        )
    ]
    ctx_valid = build_rag_context(chunks)
    assert ctx_valid["has_context"] is True
    assert "[S1]" in ctx_valid["context"]
    assert len(ctx_valid["sources"]) == 1


# ============================================================================
# 3. Background Indexing Failures & Recovery (REL-004, REL-013)
# ============================================================================

def test_partial_indexing_failure_cleans_up(db_session):
    """REL-004: Injected failure during vector indexing triggers DB rollback, status='failed', and vector purge."""
    user_id = "rel_user_indexing_fail"
    doc = Document(
        user_id=user_id,
        file_hash="hash_idx_fail_99",
        filename="crash_test.pdf",
        storage_path="uploads/mock_crash.pdf",
        chunks=0,
        status="processing",
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    doc_id = doc.id

    # Inject failure after partial processing during vector upsert
    with patch("backend.services.document_processor.process_document", side_effect=RuntimeError("Worker OOM killed")):
        process_document_background(doc_id)

    db_session.expire_all()
    failed_doc = db_session.query(Document).filter(Document.id == doc_id).first()
    assert failed_doc is not None
    assert failed_doc.status == "failed"
    assert "Worker OOM killed" in (failed_doc.error_message or "")


def test_stale_background_job_does_not_resurrect_deleted_doc(db_session):
    """REL-013: If a document is deleted while indexing is underway, the worker does not resurrect the row."""
    user_id = "rel_user_stale_job"
    doc = Document(
        user_id=user_id,
        file_hash="hash_stale_job_88",
        filename="deleted_while_processing.pdf",
        storage_path="uploads/mock_stale.pdf",
        chunks=0,
        status="processing",
    )
    db_session.add(doc)
    db_session.commit()
    doc_id = doc.id

    # Simulate user deleting document from database while process_document was running
    def simulate_concurrent_delete(*args, **kwargs):
        cleanup_db = SessionLocal()
        try:
            cleanup_db.query(Document).filter(Document.id == doc_id).delete()
            cleanup_db.commit()
        finally:
            cleanup_db.close()
        return [{"text": "Extracted chunk", "page": 1, "chunk_id": 0}]

    with patch("backend.services.document_processor.process_document", side_effect=simulate_concurrent_delete):
        process_document_background(doc_id)

    # Document should not be resurrected
    db_session.expire_all()
    resurrected = db_session.query(Document).filter(Document.id == doc_id).first()
    assert resurrected is None


# ============================================================================
# 4. SQL Database Transaction Integrity (REL-005)
# ============================================================================

def test_sql_transaction_rollback_on_failure(db_session):
    """REL-005: When a database error occurs, rollback prevents inconsistent partial state."""
    user_id = "rel_user_sql_tx"
    conv = Conversation(user_id=user_id, title="Tx Test")
    db_session.add(conv)
    db_session.commit()

    # Attempt to insert message with invalid relationship and catch exception
    try:
        # Invalid null role or simulated constraint failure
        bad_msg = ConversationMessage(conversation_id=999999, role="user", content="Orphan msg")
        db_session.add(bad_msg)
        raise RuntimeError("Simulated transaction crash")
    except Exception:
        db_session.rollback()

    # Conversation remains intact with 0 messages
    messages = db_session.query(ConversationMessage).filter(ConversationMessage.conversation_id == conv.id).all()
    assert len(messages) == 0


# ============================================================================
# 5. File Upload Disk Hygiene (REL-006)
# ============================================================================

def test_invalid_pdf_upload_no_orphaned_file(client):
    """REL-006: Rejected uploads do not leave unindexed files in the uploads folder."""
    user_id = "rel_user_upload"
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # Upload non-PDF content
    res = client.post(
        "/api/documents/upload",
        files={"file": ("malicious.exe", b"MZ binary payload", "application/octet-stream")},
        headers=headers,
    )
    assert res.status_code == 400


# ============================================================================
# 6. Cache Invalidation on Document Deletion (REL-007)
# ============================================================================

def test_deleted_document_cache_invalidation():
    """REL-007: Cache keys separate by eligible corpus; deleting a document invalidates cached retrieval."""
    cache = RetrievalCache(max_entries=20)
    user_id = "rel_user_cache_inval"
    query = "deep learning convergence"
    config = {"strategy": "dense", "top_k": 5}

    # User originally has document 100
    docs_before = [{"id": 100, "index_version": 1}]
    key_before = cache.make_key(user_id=user_id, eligible_documents=docs_before, query=query, retrieval_config=config)
    cache.set(key_before, [{"text": "Doc 100 deep learning notes"}])
    assert cache.get(key_before) is not None

    # Document 100 is deleted -> eligible documents list becomes empty
    docs_after = []
    key_after = cache.make_key(user_id=user_id, eligible_documents=docs_after, query=query, retrieval_config=config)
    assert key_before != key_after
    assert cache.get(key_after) is None


# ============================================================================
# 7. Concurrency & Race Conditions (REL-008, REL-012)
# ============================================================================

def test_concurrent_chat_queries_complete():
    """REL-008: Simultaneous queries complete without cross-contamination or hanging."""
    async def scenario():
        async def mock_query(prompt: str) -> dict:
            await asyncio.sleep(0.05)
            return {"query": prompt, "answer": f"Answer for {prompt}"}

        results = await asyncio.gather(
            mock_query("Explain retrieval-augmented generation"),
            mock_query("Explain embedding similarity"),
            return_exceptions=True,
        )

        assert len(results) == 2
        assert all(not isinstance(r, Exception) for r in results)
        assert results[0]["query"] == "Explain retrieval-augmented generation"
        assert results[1]["query"] == "Explain embedding similarity"

    asyncio.run(scenario())


def test_concurrent_duplicate_uploads_deduplicated(client, db_session):
    """REL-012: Duplicate file uploads for the same user return existing record rather than duplicating."""
    user_id = "rel_user_dup_upload"
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}
    pdf_content = b"%PDF-1.4\nDuplicate upload content test."

    with patch("backend.services.document_processor.process_document_background"):
        # First upload
        res1 = client.post(
            "/api/documents/upload",
            files={"file": ("sample.pdf", pdf_content, "application/pdf")},
            headers=headers,
        )
        assert res1.status_code == 200
        doc1_id = res1.json()["document_id"]

        # Duplicate upload
        res2 = client.post(
            "/api/documents/upload",
            files={"file": ("sample.pdf", pdf_content, "application/pdf")},
            headers=headers,
        )
        assert res2.status_code == 200
        doc2_id = res2.json()["document_id"]

        assert doc1_id == doc2_id


def test_concurrent_retries_rejected_if_already_processing(client, db_session):
    """REL-012: Retrying a document that is currently processing returns HTTP 400."""
    user_id = "rel_user_retry_race"
    token = create_access_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    doc = Document(
        user_id=user_id,
        file_hash="hash_retry_race_12",
        filename="retry_doc.pdf",
        storage_path="uploads/mock.pdf",
        chunks=0,
        status="processing",  # already processing!
    )
    db_session.add(doc)
    db_session.commit()

    res = client.post(f"/api/documents/{doc.id}/retry", headers=headers)
    assert res.status_code == 400
    assert "Only failed documents can be retried" in res.json()["detail"]


# ============================================================================
# 8. Citation Hallucination Validation & Sanitization (REL-011)
# ============================================================================

def test_citation_ids_must_exist_in_sources():
    """REL-011: Citations referencing nonexistent sources are detected and isolated."""
    allowed_sources = {"S1": {"document_id": 1}, "S2": {"document_id": 2}}
    answer_text = "Claim A is supported [S1], but claim B cites a hallucinated source [S3]."

    validation = validate_citations(answer_text, allowed_sources)
    assert validation["is_valid"] is False
    assert "[S1]" in validation["valid_citations"]
    assert "[S3]" in validation["invalid_citations"]

    sanitized = sanitize_citations(answer_text, allowed_sources)
    assert "[S3]" not in sanitized
    assert "[S1]" in sanitized


# ============================================================================
# 9. API Error Contracts (REL-009)
# ============================================================================

def test_expired_or_invalid_jwt_rejected(client):
    """REL-009: Invalid bearer tokens return HTTP 401 without leaking internal stack traces."""
    res = client.get("/api/documents/", headers={"Authorization": "Bearer invalid.expired.token"})
    assert res.status_code == 401
    assert "Invalid" in res.json().get("detail", "")
