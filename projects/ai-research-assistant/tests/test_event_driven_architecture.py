"""Unit and integration tests for Day 175: Distributed Systems & Event-Driven Architecture."""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal
from backend.events.dispatcher import OutboxDispatcher
from backend.events.publisher import create_document_with_event, record_outbox_event
from backend.events.schemas import create_event
from backend.jobs.retry_policy import RetryPolicy
from backend.jobs.tasks import index_document_job
from backend.models import Document, OutboxEvent


@pytest.fixture(autouse=True)
def clean_outbox_events():
    """Ensure OutboxEvent table is clean before and after each event-driven test."""
    db = SessionLocal()
    try:
        db.query(OutboxEvent).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(OutboxEvent).delete()
        db.commit()
    finally:
        db.close()


# ============================================================================
# 1. Architecture Documentation Verification
# ============================================================================

def test_event_driven_architecture_documentation():
    """Verify EVENT_DRIVEN_ARCHITECTURE.md and OUTBOX_PATTERN.md exist and cover core topics."""
    base_dir = Path(__file__).resolve().parent.parent
    docs_dir = base_dir / "docs" / "architecture"
    if not docs_dir.exists():
        docs_dir = base_dir.parent.parent / "docs" / "architecture"

    eda_doc = (docs_dir / "EVENT_DRIVEN_ARCHITECTURE.md").read_text(encoding="utf-8")
    outbox_doc = (docs_dir / "OUTBOX_PATTERN.md").read_text(encoding="utf-8")

    assert "Event-Driven Principles in AI Systems" in eda_doc
    assert "Commands vs. Events" in eda_doc
    assert "Delivery Guarantees & Idempotency" in eda_doc
    assert "Failure Classification & Retry Policies" in eda_doc
    assert "Dead-Letter Queues (DLQ) & Operator Replay" in eda_doc
    assert "Distributed Tracing & Correlation IDs" in eda_doc

    assert "The Dual-Write Problem" in outbox_doc
    assert "Transactional Outbox Architecture" in outbox_doc
    assert "outbox_events" in outbox_doc
    assert "The Concurrent Dispatcher Problem & Atomic Leases" in outbox_doc
    assert "Verification Under Failure Scenarios" in outbox_doc


# ============================================================================
# 2. Scenario 1: Atomic Outbox Creation & SQL Rollback Prevention
# ============================================================================

def test_create_document_with_event_atomic_success():
    """Scenario 1: create_document_with_event persists Document and OutboxEvent in a single transaction."""
    db = SessionLocal()
    try:
        new_doc = Document(
            user_id="user_event_test_1",
            file_hash="hash_atomic_12345",
            filename="atomic_paper.pdf",
            storage_path="uploads/atomic_paper.pdf",
            chunks=0,
            status="processing",
        )
        saved_doc = create_document_with_event(
            db=db,
            document=new_doc,
            user_id="user_event_test_1",
            correlation_id="corr_atomic_001",
        )
        assert saved_doc.id is not None

        # Verify corresponding outbox event was created in the same transaction
        event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == str(saved_doc.id)).first()
        assert event is not None
        assert event.event_type == "document.uploaded"
        assert event.status == "pending"
        assert event.correlation_id == "corr_atomic_001"
        assert event.event_version == 1
    finally:
        db.close()


def test_create_document_with_event_rollback_on_failure():
    """Scenario 1: If an error occurs, neither Document nor OutboxEvent is committed."""
    db = SessionLocal()
    try:
        doc = Document(
            user_id="failing_user",
            filename="fail.pdf",
            file_hash="fail_hash_999999",
            storage_path="uploads/fail.pdf",
            chunks=0,
            status="processing",
        )

        # Mock db.commit to raise an exception
        with patch.object(db, "commit", side_effect=RuntimeError("Simulated database failure")):
            try:
                create_document_with_event(db, doc, user_id="failing_user")
            except RuntimeError:
                pass

        # Verify neither outbox event nor document was committed
        evt = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == str(doc.id)).first() if doc.id else None
        assert evt is None
        saved_doc = db.query(Document).filter(Document.file_hash == "fail_hash_999999").first()
        assert saved_doc is None
    finally:
        db.close()


# ============================================================================
# 3. Scenario 2: Redis Unavailable — Event Stays Pending in Outbox
# ============================================================================

def test_redis_outage_preserves_pending_event():
    """Scenario 2: When Redis is unavailable, outbox event safely remains pending in SQL for later dispatch."""
    db = SessionLocal()
    try:
        event = record_outbox_event(
            db=db,
            event_type="document.uploaded",
            aggregate_id=8888,
            payload={"document_id": 8888, "user_id": "u_redis_down"},
            correlation_id="corr_redis_down_002",
        )
        db.commit()
        db.refresh(event)

        # Dispatcher tries to publish but broker is down
        dispatcher = OutboxDispatcher()
        with patch("backend.events.dispatcher.enqueue_document_job", side_effect=ConnectionRefusedError("Redis down")):
            stats = dispatcher.dispatch_batch(db, batch_size=10)

        # Event was retried and safely returned to pending
        db.refresh(event)
        assert event.status == "pending"
        assert event.retry_count == 1
        assert "redis down" in event.last_error.lower()
        assert stats["retried"] >= 1
    finally:
        db.close()


# ============================================================================
# 4. Scenario 3: Dispatcher Crash & Lease Expiration (Duplicate Delivery Safe)
# ============================================================================

def test_dispatcher_crash_and_stale_lease_recovery():
    """Scenario 3: If dispatcher crashes mid-publish, stale lease expires and event is reclaimed."""
    db = SessionLocal()
    try:
        event = record_outbox_event(
            db=db,
            event_type="document.uploaded",
            aggregate_id=7777,
            payload={"document_id": 7777, "user_id": "u_crash"},
            correlation_id="corr_crash_003",
        )
        # Simulate previous crashed dispatcher claiming event 10 minutes ago
        event.status = "publishing"
        event.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        db.commit()

        dispatcher = OutboxDispatcher(lease_timeout_seconds=300.0)
        # Claiming should reclaim the stale event
        claimed = dispatcher.claim_pending_events(db)
        claimed_ids = [c.id for c in claimed]
        assert event.id in claimed_ids

        db.refresh(event)
        assert event.status == "publishing"
        # Lease timestamp refreshed
        assert (datetime.now(timezone.utc) - event.claimed_at.replace(tzinfo=timezone.utc)).total_seconds() < 10
    finally:
        db.close()


# ============================================================================
# 5. Scenario 4: Concurrent Workers Race on Same Document Job
# ============================================================================

def test_concurrent_worker_race_claims_document_once():
    """Scenario 4: When two workers process the same document job, only one performs indexing while second skips."""
    db = SessionLocal()
    try:
        doc = Document(
            user_id="user_race_test",
            file_hash="hash_race_9999",
            filename="race_doc.pdf",
            storage_path="uploads/race_doc.pdf",
            chunks=0,
            status="uploaded",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        with patch("backend.jobs.tasks.process_document_background") as mock_proc:
            # First worker claims and processes
            res1 = index_document_job(document_id=doc.id, correlation_id="corr_worker_1")
            # Mark document as indexed to simulate first worker completion
            doc.status = "indexed"
            doc.chunks = 5
            db.commit()

            # Second worker attempts duplicate execution
            res2 = index_document_job(document_id=doc.id, correlation_id="corr_worker_2")

        # Worker 1 proceeded
        assert res1["idempotent_skip"] is False
        assert mock_proc.call_count == 1

        # Worker 2 skipped duplicate work
        assert res2["idempotent_skip"] is True
        assert res2["status"] == "indexed"
        assert res2["chunks"] == 5
    finally:
        db.close()


# ============================================================================
# 6. Scenario 5: Retry Budget Exhausted -> Dead-Letter Queue & Replay
# ============================================================================

def test_retry_exhaustion_moves_to_dead_letter_and_replays():
    """Scenario 5: When max retries are exceeded, event moves to dead_letter and can be replayed."""
    db = SessionLocal()
    try:
        event = record_outbox_event(
            db=db,
            event_type="document.uploaded",
            aggregate_id=6666,
            payload={"document_id": 6666, "user_id": "u_dlq"},
            correlation_id="corr_dlq_005",
        )
        # Event is already at attempt 2 of 3
        event.retry_count = 2
        event.max_retries = 3
        db.commit()
        db.refresh(event)

        dispatcher = OutboxDispatcher()
        with patch("backend.events.dispatcher.enqueue_document_job", side_effect=TimeoutError("Repeated timeout")):
            stats = dispatcher.dispatch_batch(db, batch_size=10)

        db.refresh(event)
        # Attempt 3 failed -> moved to dead_letter
        assert event.status == "dead_letter"
        assert event.retry_count == 3
        assert stats["dead_letter"] == 1

        # Operator triggers controlled replay
        replayed = dispatcher.replay_dead_letter_event(db, event.id)
        assert replayed is True

        db.refresh(event)
        assert event.status == "pending"
        assert event.retry_count == 0
        assert event.last_error is None
    finally:
        db.close()


# ============================================================================
# 7. Failure Classification & Exponential Backoff
# ============================================================================

def test_retry_policy_classification_and_backoff():
    """Verify RetryPolicy failure classification and exponential delay calculation with jitter."""
    policy = RetryPolicy(
        max_retries=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=30.0,
        backoff_multiplier=2.0,
        jitter=True,
    )

    # Transient error classification
    assert policy.is_transient_error(TimeoutError("Connection timed out")) is True
    assert policy.is_transient_error(RuntimeError("429 Resource Exhausted: Rate limit")) is True
    assert policy.is_transient_error(ConnectionResetError("Broker connection reset")) is True

    # Permanent error classification
    assert policy.is_transient_error(ValueError("Invalid API key configured")) is False
    assert policy.is_transient_error(FileNotFoundError("File does not have a valid PDF signature")) is False

    # Backoff calculation: attempt 1 -> ~1.0s, attempt 2 -> ~2.0s, attempt 3 -> ~4.0s
    d1 = policy.calculate_delay(1)
    d2 = policy.calculate_delay(2)
    d3 = policy.calculate_delay(3)

    assert d1 >= 1.0
    assert d2 >= 2.0
    assert d3 >= 4.0
    assert d1 < d2 < d3


# ============================================================================
# 8. Event Versioning & Schemas
# ============================================================================

def test_event_schema_versioning():
    """Verify EventHeader and create_event produce consistent versioned payloads."""
    evt = create_event(
        event_type="document.uploaded",
        aggregate_id="doc_999",
        payload={"filename": "test.pdf", "user_id": "u1"},
        correlation_id="corr_ver_123",
        version=1,
    )

    assert evt["event_type"] == "document.uploaded"
    assert evt["event_version"] == 1
    assert evt["aggregate_id"] == "doc_999"
    assert evt["correlation_id"] == "corr_ver_123"
    assert "occurred_at" in evt
    assert evt["payload"]["filename"] == "test.pdf"
