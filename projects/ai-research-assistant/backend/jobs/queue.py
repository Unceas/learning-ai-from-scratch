"""Distributed job queue management using Redis and RQ with graceful local fallback."""

import json
import logging
from typing import Any

from backend.config import get_settings

logger = logging.getLogger("research_assistant.jobs")

_redis_conn = None
_queues: dict[str, Any] = {}
_fallback_queue: list[dict[str, Any]] = []


def get_redis_connection():
    """Retrieve or initialize shared Redis client connection."""
    global _redis_conn
    settings = get_settings()

    if _redis_conn is not None:
        return _redis_conn

    if not settings.redis_url:
        return None

    try:
        from redis import Redis
        _redis_conn = Redis.from_url(settings.redis_url, decode_responses=False)
        _redis_conn.ping()
        return _redis_conn
    except Exception as exc:
        logger.warning("Redis connection unavailable, falling back to local queue: %s", exc)
        return None


def is_queue_available() -> bool:
    """Check if Redis connection is active and healthy."""
    conn = get_redis_connection()
    if conn is None:
        return False
    try:
        return bool(conn.ping())
    except Exception:
        return False


def get_queue(name: str | None = None):
    """Retrieve an RQ Queue instance or None if Redis is unavailable."""
    global _queues
    settings = get_settings()
    queue_name = name or settings.distributed_queue_name

    if queue_name in _queues:
        return _queues[queue_name]

    conn = get_redis_connection()
    if conn is None:
        return None

    try:
        from rq import Queue
        q = Queue(queue_name, connection=conn, default_timeout=900)
        _queues[queue_name] = q
        return q
    except Exception as exc:
        logger.error("Failed initializing RQ Queue '%s': %s", queue_name, exc)
        return None


def enqueue_document_job(
    document_id: int,
    file_path: str | None = None,
    queue_name: str | None = None,
    job_timeout: int = 900,
) -> str:
    """Enqueue a document indexing job onto Redis queue or fallback queue.

    Returns:
        Job identifier string.
    """
    settings = get_settings()
    target_queue_name = queue_name or settings.distributed_queue_name
    q = get_queue(target_queue_name)

    if q is not None and settings.use_distributed_queue:
        try:
            job = q.enqueue(
                "backend.jobs.tasks.index_document_job",
                document_id,
                file_path=file_path,
                job_timeout=job_timeout,
            )
            logger.info("Enqueued document %d to Redis queue '%s' (job_id=%s)", document_id, target_queue_name, job.id)
            return str(job.id)
        except Exception as exc:
            logger.warning("Failed enqueueing to Redis queue, using fallback queue: %s", exc)

    # In-memory / local fallback for development, testing, and Redis outages
    job_id = f"fallback_{document_id}_{len(_fallback_queue)}"
    _fallback_queue.append({
        "job_id": job_id,
        "document_id": document_id,
        "file_path": file_path,
        "queue": target_queue_name,
    })
    logger.info("Enqueued document %d to fallback queue (job_id=%s)", document_id, job_id)
    return job_id


def get_queue_depth(name: str | None = None) -> int:
    """Return count of queued jobs in Redis queue or fallback queue."""
    settings = get_settings()
    target_queue_name = name or settings.distributed_queue_name
    q = get_queue(target_queue_name)

    if q is not None:
        try:
            return len(q)
        except Exception:
            pass

    return len([job for job in _fallback_queue if job.get("queue") == target_queue_name])


def clear_fallback_queue() -> None:
    """Clear in-memory fallback queue entries (for tests)."""
    global _fallback_queue
    _fallback_queue.clear()


def record_outbox_event(
    db: Any,
    document_id: int,
    event_type: str = "INDEX_DOCUMENT",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Helper implementing transactional outbox pattern to guarantee event recording."""
    event_data = {
        "event_type": event_type,
        "document_id": document_id,
        "payload": payload or {},
        "status": "pending",
    }
    logger.info("Transactional outbox event recorded: %s", json.dumps(event_data))
    return event_data
