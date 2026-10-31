"""Jobs package for distributed background task execution."""

from backend.jobs.queue import (
    enqueue_document_job,
    get_queue,
    get_queue_depth,
    is_queue_available,
)
from backend.jobs.tasks import index_document_job

__all__ = [
    "enqueue_document_job",
    "get_queue",
    "get_queue_depth",
    "index_document_job",
    "is_queue_available",
]
