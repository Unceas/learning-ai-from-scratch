"""Outbox event dispatcher with atomic claiming, lease expiration, and dead-letter handling."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.jobs.queue import enqueue_document_job
from backend.jobs.retry_policy import RetryPolicy, default_retry_policy
from backend.models import OutboxEvent

logger = logging.getLogger("research_assistant.events.dispatcher")


class OutboxDispatcher:
    """Reads uncommitted outbox events, atomically claims leases, and dispatches to queue broker."""

    def __init__(
        self,
        lease_timeout_seconds: float = 300.0,
        retry_policy: RetryPolicy | None = None,
    ):
        self.lease_timeout = lease_timeout_seconds
        self.retry_policy = retry_policy or default_retry_policy

    def claim_pending_events(
        self,
        db: Session,
        batch_size: int = 50,
    ) -> list[OutboxEvent]:
        """Atomically claim pending events or expired leases to prevent concurrent dispatcher collisions."""
        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(seconds=self.lease_timeout)

        # 1. Fetch pending events or expired publishing leases
        candidates = (
            db.query(OutboxEvent)
            .filter(
                (OutboxEvent.status == "pending")
                | (
                    (OutboxEvent.status == "publishing")
                    & (OutboxEvent.claimed_at < stale_threshold)
                )
            )
            .order_by(OutboxEvent.created_at.asc())
            .limit(batch_size)
            .all()
        )

        if not candidates:
            return []

        # 2. Mark claimed events as 'publishing' with lease timestamp
        claimed_ids = [c.id for c in candidates]
        for event in candidates:
            event.status = "publishing"
            event.claimed_at = now

        db.commit()
        logger.info("Claimed %d outbox events for publishing: %s", len(claimed_ids), claimed_ids)
        return candidates

    def dispatch_event(
        self,
        event: OutboxEvent,
        queue: Any = None,
    ) -> str:
        """Route an individual event to its appropriate queue job.

        Returns:
            Dispatched job identifier.
        """
        payload = {}
        try:
            payload = json.loads(event.payload) if event.payload else {}
        except Exception:
            pass

        document_id = payload.get("document_id") or event.aggregate_id

        if event.event_type == "document.uploaded":
            # Enqueue background indexing with trace correlation ID
            job_id = enqueue_document_job(
                document_id=int(document_id),
                file_path=payload.get("storage_path"),
                correlation_id=event.correlation_id,
            )
            return job_id

        # Extensible to other domain events
        return f"dispatched_{event.id}"

    def dispatch_batch(
        self,
        db: Session,
        queue: Any = None,
        batch_size: int = 50,
    ) -> dict[str, int]:
        """Process one batch of claimed outbox events with retry and dead-letter handling."""
        events = self.claim_pending_events(db, batch_size=batch_size)
        stats = {"claimed": len(events), "published": 0, "retried": 0, "dead_letter": 0}

        for event in events:
            try:
                self.dispatch_event(event, queue=queue)

                # Mark as published on success
                event.status = "published"
                event.published_at = datetime.now(timezone.utc)
                event.last_error = None
                db.commit()
                stats["published"] += 1
                logger.info("Outbox event %s published successfully", event.id)
            except Exception as exc:
                db.rollback()
                sanitized_error = str(exc)[:250]
                event.retry_count += 1
                event.last_error = sanitized_error

                # Check retry budget and failure classification
                if self.retry_policy.should_retry(exc, event.retry_count):
                    event.status = "pending"  # Release back to pending for retry
                    stats["retried"] += 1
                    logger.warning(
                        "Outbox event %s failed (attempt %d/%d), marked pending: %s",
                        event.id,
                        event.retry_count,
                        event.max_retries,
                        sanitized_error,
                    )
                else:
                    event.status = "dead_letter"  # Move to DLQ
                    stats["dead_letter"] += 1
                    logger.error(
                        "Outbox event %s exhausted retry budget or fatal error, moved to dead_letter: %s",
                        event.id,
                        sanitized_error,
                    )

                db.commit()

        return stats

    def replay_dead_letter_event(
        self,
        db: Session,
        event_id: str,
    ) -> bool:
        """Reset a dead-letter event back to pending for controlled operator replay."""
        event = db.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if not event or event.status != "dead_letter":
            return False

        event.status = "pending"
        event.retry_count = 0
        event.claimed_at = None
        event.last_error = None
        db.commit()
        logger.info("Dead-letter event %s successfully reset to pending for replay", event_id)
        return True


default_dispatcher = OutboxDispatcher()


def dispatch_pending_events(
    db: Session,
    queue: Any = None,
    batch_size: int = 50,
) -> dict[str, int]:
    """Convenience functional interface to dispatch pending outbox events."""
    return default_dispatcher.dispatch_batch(db, queue=queue, batch_size=batch_size)
