"""Versioned Pydantic schemas for event-driven architecture."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EventHeader(BaseModel):
    """Standardized metadata header for versioned events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    event_version: int = 1
    aggregate_id: str
    correlation_id: str | None = None
    occurred_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class BaseEvent(BaseModel):
    """Base event model combining header and typed payload."""
    header: EventHeader
    payload: dict[str, Any]


class DocumentUploadedPayload(BaseModel):
    """Payload for 'document.uploaded' event."""
    document_id: int
    user_id: str
    filename: str
    file_hash: str
    storage_path: str


class DocumentIndexingStartedPayload(BaseModel):
    """Payload for 'document.indexing.started' event."""
    document_id: int
    user_id: str
    attempt: int = 1


class DocumentIndexedPayload(BaseModel):
    """Payload for 'document.indexed' event."""
    document_id: int
    user_id: str
    chunks: int
    index_version: int


class DocumentIndexingFailedPayload(BaseModel):
    """Payload for 'document.indexing.failed' event."""
    document_id: int
    user_id: str
    error_message: str
    attempt: int
    retryable: bool


class DocumentDeletedPayload(BaseModel):
    """Payload for 'document.deleted' event."""
    document_id: int
    user_id: str
    file_hash: str


def create_event(
    event_type: str,
    aggregate_id: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Helper factory to construct a standardized versioned event dictionary."""
    header = EventHeader(
        event_type=event_type,
        event_version=version,
        aggregate_id=str(aggregate_id),
        correlation_id=correlation_id,
    )
    return {
        "event_id": header.event_id,
        "event_type": header.event_type,
        "event_version": header.event_version,
        "aggregate_id": header.aggregate_id,
        "correlation_id": header.correlation_id,
        "occurred_at": header.occurred_at,
        "payload": payload,
    }
