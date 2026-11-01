"""Transactional Outbox event publisher ensuring atomic business state and event writes."""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.events.schemas import create_event
from backend.models import Document, OutboxEvent

logger = logging.getLogger("research_assistant.events")


def record_outbox_event(
    db: Session,
    event_type: str,
    aggregate_id: str | int,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    version: int = 1,
) -> OutboxEvent:
    """Record an outbox event within the caller's active database transaction.

    Args:
        db: SQLAlchemy database session.
        event_type: Canonical event name (e.g. 'document.uploaded').
        aggregate_id: Unique identifier of the entity/aggregate.
        payload: Event body dictionary.
        correlation_id: Optional distributed tracing correlation identifier.
        version: Event schema version.

    Returns:
        Uncommitted or active OutboxEvent model instance.
    """
    event_id = str(uuid.uuid4())
    event_data = create_event(
        event_type=event_type,
        aggregate_id=str(aggregate_id),
        payload=payload,
        correlation_id=correlation_id,
        version=version,
    )
    event_record = OutboxEvent(
        id=event_id,
        event_type=event_type,
        event_version=version,
        aggregate_id=str(aggregate_id),
        correlation_id=correlation_id,
        payload=json.dumps(event_data.get("payload", payload)),
        status="pending",
    )
    db.add(event_record)
    return event_record


def create_document_with_event(
    db: Session,
    document: Document,
    user_id: str,
    correlation_id: str | None = None,
) -> Document:
    """Atomically commit document metadata and corresponding 'document.uploaded' outbox event.

    Guarantees no dual-write inconsistencies: either both records persist or both roll back.

    Args:
        db: SQLAlchemy session.
        document: Populated Document model instance.
        user_id: Authenticated user identifier.
        correlation_id: Correlation identifier for distributed tracing.

    Returns:
        Persisted Document model instance.

    Raises:
        Exception: If database commit fails; rolls back both records.
    """
    try:
        # Step 1: Add document to session and flush to obtain auto-generated document.id
        db.add(document)
        db.flush()

        # Step 2: Construct outbox event with resolved document.id
        payload = {
            "document_id": document.id,
            "user_id": str(user_id),
            "filename": document.filename,
            "file_hash": document.file_hash,
            "storage_path": document.storage_path,
        }
        event_record = record_outbox_event(
            db=db,
            event_type="document.uploaded",
            aggregate_id=document.id,
            payload=payload,
            correlation_id=correlation_id,
            version=1,
        )

        # Step 3: Atomic commit of both entities
        db.commit()
        db.refresh(document)
        logger.info(
            "Atomic transaction committed: document_id=%d, outbox_event_id=%s, correlation_id=%s",
            document.id,
            event_record.id,
            correlation_id,
        )
        return document
    except Exception as exc:
        db.rollback()
        logger.error("Failed atomic document and outbox event creation, rolled back: %s", exc)
        raise
