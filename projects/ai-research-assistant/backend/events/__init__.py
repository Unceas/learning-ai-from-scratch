"""Events package providing versioned schemas, atomic outbox publishing, and concurrent dispatching."""

from backend.events.dispatcher import (
    OutboxDispatcher,
    default_dispatcher,
    dispatch_pending_events,
)
from backend.events.publisher import (
    create_document_with_event,
    record_outbox_event,
)
from backend.events.schemas import (
    BaseEvent,
    DocumentDeletedPayload,
    DocumentIndexedPayload,
    DocumentIndexingFailedPayload,
    DocumentIndexingStartedPayload,
    DocumentUploadedPayload,
    EventHeader,
    create_event,
)

__all__ = [
    "BaseEvent",
    "DocumentDeletedPayload",
    "DocumentIndexedPayload",
    "DocumentIndexingFailedPayload",
    "DocumentIndexingStartedPayload",
    "DocumentUploadedPayload",
    "EventHeader",
    "OutboxDispatcher",
    "create_document_with_event",
    "create_event",
    "default_dispatcher",
    "dispatch_pending_events",
    "record_outbox_event",
]
