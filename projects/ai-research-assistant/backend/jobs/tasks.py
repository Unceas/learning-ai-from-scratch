"""Distributed background tasks for document indexing and vector processing with idempotent claims."""

import logging
from typing import Any

from backend.database import SessionLocal
from backend.events.publisher import record_outbox_event
from backend.models import Document
from backend.services.document_processor import process_document_background

logger = logging.getLogger("research_assistant.jobs.tasks")


def index_document_job(
    document_id: int,
    file_path: str | None = None,
    force_reindex: bool = False,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Execute background document indexing task with atomic claiming and guaranteed idempotency.

    Args:
        document_id: Database identifier of the document to index.
        file_path: Optional explicit filesystem or storage path.
        force_reindex: If True, reindex even if document status is already 'indexed'.
        correlation_id: Optional correlation identifier for distributed tracing.

    Returns:
        Dictionary summarizing execution outcome.
    """
    db = SessionLocal()
    try:
        # Step 1: Document existence & state pre-check
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("[Corr: %s] Job aborted: Document %d does not exist in database.", correlation_id, document_id)
            return {
                "document_id": document_id,
                "status": "not_found",
                "idempotent_skip": False,
                "correlation_id": correlation_id,
            }

        # Step 2: Idempotency check: Skip duplicate job execution if already indexed
        if not force_reindex and document.status == "indexed" and (document.chunks or 0) > 0:
            logger.info("[Corr: %s] Job idempotent skip: Document %d already indexed (%d chunks).", correlation_id, document_id, document.chunks)
            return {
                "document_id": document_id,
                "status": "indexed",
                "chunks": document.chunks,
                "idempotent_skip": True,
                "correlation_id": correlation_id,
            }

        # Step 3: Atomic claim transition: only one concurrent worker successfully claims the document
        claimed_count = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                Document.status.in_(["uploaded", "failed", "processing"]),
            )
            .update(
                {
                    "status": "processing",
                    "processing_attempts": Document.processing_attempts + 1,
                },
                synchronize_session=False,
            )
        )
        db.commit()

        if claimed_count == 0 and not force_reindex:
            db.expire_all()
            doc_state = db.query(Document).filter(Document.id == document_id).first()
            logger.info(
                "[Corr: %s] Document %d claimed by another concurrent worker or already processed (status=%s)",
                correlation_id,
                document_id,
                doc_state.status if doc_state else "none",
            )
            return {
                "document_id": document_id,
                "status": doc_state.status if doc_state else "unknown",
                "chunks": doc_state.chunks if doc_state else 0,
                "idempotent_skip": True,
                "correlation_id": correlation_id,
            }

        # Step 4: Record 'document.indexing.started' event
        try:
            record_outbox_event(
                db=db,
                event_type="document.indexing.started",
                aggregate_id=document_id,
                payload={"document_id": document_id, "attempt": document.processing_attempts},
                correlation_id=correlation_id,
                version=1,
            )
            db.commit()
        except Exception:
            db.rollback()

        # Step 5: Execute processing pipeline (PDF parsing, chunking, embedding, vector store upsert)
        process_document_background(document_id=document_id, file_path=file_path)

        # Step 6: Refresh document state and record outcome event
        db.expire_all()
        doc_updated = db.query(Document).filter(Document.id == document_id).first()

        if doc_updated and doc_updated.status == "indexed":
            try:
                record_outbox_event(
                    db=db,
                    event_type="document.indexed",
                    aggregate_id=document_id,
                    payload={
                        "document_id": document_id,
                        "chunks": doc_updated.chunks,
                        "index_version": doc_updated.index_version,
                    },
                    correlation_id=correlation_id,
                    version=1,
                )
                db.commit()
            except Exception:
                db.rollback()
        elif doc_updated and doc_updated.status == "failed":
            try:
                record_outbox_event(
                    db=db,
                    event_type="document.indexing.failed",
                    aggregate_id=document_id,
                    payload={
                        "document_id": document_id,
                        "error_message": doc_updated.error_message or "Unknown failure",
                        "attempt": doc_updated.processing_attempts,
                    },
                    correlation_id=correlation_id,
                    version=1,
                )
                db.commit()
            except Exception:
                db.rollback()

        return {
            "document_id": document_id,
            "status": doc_updated.status if doc_updated else "unknown",
            "chunks": doc_updated.chunks if doc_updated else 0,
            "idempotent_skip": False,
            "correlation_id": correlation_id,
        }
    except Exception as exc:
        logger.error("[Corr: %s] Job execution failed for document %d: %s", correlation_id, document_id, exc)
        raise
    finally:
        db.close()
