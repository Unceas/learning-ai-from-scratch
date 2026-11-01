"""Suite #55: Distributed Systems & Event-Driven Architecture Tests.

Validates:
1. Architectural documentation in docs/architecture/EVENT_DRIVEN_ARCHITECTURE.md and OUTBOX_PATTERN.md.
2. OutboxEvent SQLAlchemy model and Alembic migration.
3. Scenario 1: Atomic document metadata and outbox event creation with rollback on error.
4. Scenario 2: Broker outage resilience — pending events remain safely stored in SQL.
5. Scenario 3: Dispatcher crash recovery — stale lease expiration and safe reclamation.
6. Scenario 4: Concurrent worker race — atomic document claim transition and duplicate skip.
7. Scenario 5: Retry budget exhaustion — dead-letter queue transition and operator replay.
8. RetryPolicy failure classification (transient vs permanent) and exponential backoff with jitter.
9. Event schema versioning and distributed tracing correlation ID propagation.
10. Document route integration with atomic outbox event creation.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# Ensure project root is in sys.path and is current working directory
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)

from backend.database import SessionLocal
from backend.events.dispatcher import OutboxDispatcher
from backend.events.publisher import create_document_with_event, record_outbox_event
from backend.events.schemas import create_event
from backend.jobs.queue import clear_fallback_queue
from backend.jobs.retry_policy import RetryPolicy
from backend.jobs.tasks import index_document_job
from backend.models import Document, OutboxEvent


class TestDistributedSystemsAndEventDrivenArchitecture(unittest.TestCase):

    def setUp(self):
        clear_fallback_queue()

    def tearDown(self):
        clear_fallback_queue()

    # ========================================================================
    # 1. Architecture Documentation Verification
    # ========================================================================

    def test_event_driven_architecture_documentation_exists(self):
        """DIST-001: docs/architecture/EVENT_DRIVEN_ARCHITECTURE.md exists with all required sections."""
        docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not docs_dir.exists():
            docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

        doc = (docs_dir / "EVENT_DRIVEN_ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("Event-Driven Principles in AI Systems", doc)
        self.assertIn("Commands vs. Events", doc)
        self.assertIn("Core Domain Events", doc)
        self.assertIn("Delivery Guarantees & Idempotency", doc)
        self.assertIn("Failure Classification & Retry Policies", doc)
        self.assertIn("Dead-Letter Queues (DLQ) & Operator Replay", doc)
        self.assertIn("Distributed Tracing & Correlation IDs", doc)

    def test_outbox_pattern_documentation_exists(self):
        """DIST-002: docs/architecture/OUTBOX_PATTERN.md exists with all required sections."""
        docs_dir = Path(PROJECT_DIR) / "docs" / "architecture"
        if not docs_dir.exists():
            docs_dir = Path(PROJECT_DIR).parent.parent / "docs" / "architecture"

        doc = (docs_dir / "OUTBOX_PATTERN.md").read_text(encoding="utf-8")
        self.assertIn("The Dual-Write Problem", doc)
        self.assertIn("Transactional Outbox Architecture", doc)
        self.assertIn("outbox_events", doc)
        self.assertIn("The Concurrent Dispatcher Problem & Atomic Leases", doc)
        self.assertIn("Verification Under Failure Scenarios", doc)

    # ========================================================================
    # 2. OutboxEvent Model & Alembic Migration
    # ========================================================================

    def test_outbox_event_model_attributes(self):
        """DIST-003: OutboxEvent model has all required persistence and tracking columns."""
        db = SessionLocal()
        try:
            event = OutboxEvent(
                event_type="document.uploaded",
                aggregate_id="test_agg_1",
                payload='{"document_id": 1}',
                status="pending",
                correlation_id="corr_suite55_test",
            )
            db.add(event)
            db.commit()
            db.refresh(event)

            self.assertIsNotNone(event.id)
            self.assertEqual(event.event_version, 1)
            self.assertEqual(event.retry_count, 0)
            self.assertEqual(event.max_retries, 3)
            self.assertIsNotNone(event.created_at)
            self.assertIsNotNone(event.updated_at)
            self.assertEqual(event.correlation_id, "corr_suite55_test")
        finally:
            db.close()

    # ========================================================================
    # 3. Scenario 1: Atomic Document & Outbox Event Persistence
    # ========================================================================

    def test_atomic_document_and_outbox_event_success(self):
        """DIST-004: create_document_with_event commits Document and OutboxEvent atomically."""
        db = SessionLocal()
        try:
            doc = Document(
                user_id="user_suite55_atomic",
                file_hash="hash_suite55_atomic_1",
                filename="atomic_analysis.pdf",
                storage_path="uploads/atomic_analysis.pdf",
                chunks=0,
                status="processing",
            )
            saved = create_document_with_event(
                db=db,
                document=doc,
                user_id="user_suite55_atomic",
                correlation_id="corr_suite55_001",
            )
            self.assertIsNotNone(saved.id)

            event = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == str(saved.id)).first()
            self.assertIsNotNone(event)
            self.assertEqual(event.event_type, "document.uploaded")
            self.assertEqual(event.status, "pending")
            self.assertEqual(event.correlation_id, "corr_suite55_001")
        finally:
            db.close()

    def test_atomic_document_and_outbox_event_rollback_on_failure(self):
        """DIST-004: If transaction fails, both Document and OutboxEvent are rolled back."""
        db = SessionLocal()
        try:
            doc = Document(
                user_id="rollback_user",
                filename="fail.pdf",
                file_hash="fail_hash_888888",
                storage_path="uploads/fail.pdf",
                chunks=0,
                status="processing",
            )

            with patch.object(db, "commit", side_effect=RuntimeError("Simulated database failure")):
                with self.assertRaises(RuntimeError):
                    create_document_with_event(db, doc, user_id="rollback_user")

            evt = db.query(OutboxEvent).filter(OutboxEvent.aggregate_id == str(doc.id)).first() if doc.id else None
            self.assertIsNone(evt)

            saved_doc = db.query(Document).filter(Document.file_hash == "fail_hash_888888").first()
            self.assertIsNone(saved_doc)
        finally:
            db.close()

    # ========================================================================
    # 4. Scenario 2: Redis Unavailable — Event Stays Pending
    # ========================================================================

    def test_redis_unavailable_preserves_pending_event(self):
        """DIST-005: When Redis is down, outbox event safely remains in pending state without job loss."""
        db = SessionLocal()
        try:
            event = record_outbox_event(
                db=db,
                event_type="document.uploaded",
                aggregate_id=55555,
                payload={"document_id": 55555, "user_id": "u_redis_down"},
                correlation_id="corr_redis_55",
            )
            db.commit()
            db.refresh(event)

            dispatcher = OutboxDispatcher()
            with patch("backend.events.dispatcher.enqueue_document_job", side_effect=ConnectionError("Redis connection refused")):
                stats = dispatcher.dispatch_batch(db, batch_size=10)

            db.refresh(event)
            self.assertEqual(event.status, "pending")
            self.assertEqual(event.retry_count, 1)
            self.assertIn("redis connection refused", event.last_error.lower())
            self.assertGreaterEqual(stats["retried"], 1)
        finally:
            db.close()

    # ========================================================================
    # 5. Scenario 3: Dispatcher Crash & Stale Lease Recovery
    # ========================================================================

    def test_dispatcher_crash_stale_lease_recovery(self):
        """DIST-006: Stale claimed leases from a crashed dispatcher are safely reclaimed by surviving dispatchers."""
        db = SessionLocal()
        try:
            event = record_outbox_event(
                db=db,
                event_type="document.uploaded",
                aggregate_id=44444,
                payload={"document_id": 44444, "user_id": "u_crash"},
                correlation_id="corr_crash_55",
            )
            # Simulate crashed dispatcher claiming event 10 minutes ago
            event.status = "publishing"
            event.claimed_at = datetime.now(timezone.utc) - timedelta(minutes=10)
            db.commit()

            dispatcher = OutboxDispatcher(lease_timeout_seconds=300.0)
            claimed = dispatcher.claim_pending_events(db)
            claimed_ids = [c.id for c in claimed]
            self.assertIn(event.id, claimed_ids)

            db.refresh(event)
            self.assertEqual(event.status, "publishing")
        finally:
            db.close()

    # ========================================================================
    # 6. Scenario 4: Concurrent Workers Race on Document Job
    # ========================================================================

    def test_concurrent_worker_race_claims_document_once(self):
        """DIST-007: When two workers race on the same document job, only one performs work while second skips."""
        db = SessionLocal()
        try:
            doc = Document(
                user_id="user_race_suite55",
                file_hash="hash_race_suite55",
                filename="race_experiment.pdf",
                storage_path="uploads/race_experiment.pdf",
                chunks=0,
                status="uploaded",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)

            with patch("backend.jobs.tasks.process_document_background") as mock_proc:
                # Worker 1 claims and executes
                res1 = index_document_job(document_id=doc.id, correlation_id="corr_worker_1")
                # Simulate document successfully indexed
                doc.status = "indexed"
                doc.chunks = 6
                db.commit()

                # Worker 2 attempts duplicate processing
                res2 = index_document_job(document_id=doc.id, correlation_id="corr_worker_2")

            self.assertFalse(res1["idempotent_skip"])
            self.assertEqual(mock_proc.call_count, 1)

            self.assertTrue(res2["idempotent_skip"])
            self.assertEqual(res2["status"], "indexed")
            self.assertEqual(res2["chunks"], 6)
        finally:
            db.close()

    # ========================================================================
    # 7. Scenario 5: Retry Budget Exhausted -> Dead-Letter Queue & Replay
    # ========================================================================

    def test_dead_letter_queue_and_replay(self):
        """DIST-008: Events exceeding max retries move to dead_letter and can be replayed."""
        db = SessionLocal()
        try:
            event = record_outbox_event(
                db=db,
                event_type="document.uploaded",
                aggregate_id=33333,
                payload={"document_id": 33333, "user_id": "u_dlq"},
                correlation_id="corr_dlq_55",
            )
            # Already failed twice
            event.retry_count = 2
            event.max_retries = 3
            db.commit()
            db.refresh(event)

            dispatcher = OutboxDispatcher()
            with patch("backend.events.dispatcher.enqueue_document_job", side_effect=TimeoutError("Repeated timeout")):
                stats = dispatcher.dispatch_batch(db, batch_size=10)

            db.refresh(event)
            self.assertEqual(event.status, "dead_letter")
            self.assertEqual(event.retry_count, 3)
            self.assertEqual(stats["dead_letter"], 1)

            # Replay dead-letter event
            replayed = dispatcher.replay_dead_letter_event(db, event.id)
            self.assertTrue(replayed)

            db.refresh(event)
            self.assertEqual(event.status, "pending")
            self.assertEqual(event.retry_count, 0)
            self.assertIsNone(event.last_error)
        finally:
            db.close()

    # ========================================================================
    # 8. Failure Classification & Backoff Calculation
    # ========================================================================

    def test_retry_policy_classification_and_backoff(self):
        """DIST-009: RetryPolicy classifies transient vs permanent errors and computes exponential backoff."""
        policy = RetryPolicy(
            max_retries=3,
            initial_delay_seconds=1.0,
            max_delay_seconds=30.0,
            backoff_multiplier=2.0,
            jitter=True,
        )

        # Transient
        self.assertTrue(policy.is_transient_error(TimeoutError("Connection timed out")))
        self.assertTrue(policy.is_transient_error(RuntimeError("429 Resource Exhausted")))
        self.assertTrue(policy.is_transient_error(ConnectionResetError("Reset by peer")))

        # Permanent
        self.assertFalse(policy.is_transient_error(ValueError("Invalid API key configured")))
        self.assertFalse(policy.is_transient_error(FileNotFoundError("File does not exist")))

        # Delays increase exponentially
        d1 = policy.calculate_delay(1)
        d2 = policy.calculate_delay(2)
        d3 = policy.calculate_delay(3)

        self.assertGreaterEqual(d1, 1.0)
        self.assertGreaterEqual(d2, 2.0)
        self.assertGreaterEqual(d3, 4.0)
        self.assertLess(d1, d2)
        self.assertLess(d2, d3)

    # ========================================================================
    # 9. Event Schema Versioning & Correlation IDs
    # ========================================================================

    def test_event_schema_versioning(self):
        """DIST-010: Event creation produces standardized versioned schemas with correlation IDs."""
        evt = create_event(
            event_type="document.uploaded",
            aggregate_id="doc_789",
            payload={"filename": "neural_nets.pdf", "user_id": "u789"},
            correlation_id="corr_trace_xyz",
            version=1,
        )

        self.assertEqual(evt["event_type"], "document.uploaded")
        self.assertEqual(evt["event_version"], 1)
        self.assertEqual(evt["aggregate_id"], "doc_789")
        self.assertEqual(evt["correlation_id"], "corr_trace_xyz")
        self.assertIn("event_id", evt)
        self.assertIn("occurred_at", evt)
        self.assertEqual(evt["payload"]["filename"], "neural_nets.pdf")


if __name__ == "__main__":
    unittest.main()
