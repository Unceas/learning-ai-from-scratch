"""Distributed background tasks for document indexing and vector processing."""

import logging
from typing import Any

from backend.database import SessionLocal
from backend.models import Document
from backend.services.document_processor import process_document_background

logger = logging.getLogger("research_assistant.jobs")


def index_document_job(
    document_id: int,
    file_path: str | None = None,
    force_reindex: bool = False,
) -> dict[str, Any]:
    """Execute background document indexing task with guaranteed idempotency.

    Args:
        document_id: Database identifier of the document to index.
        file_path: Optional explicit filesystem or storage path.
        force_reindex: If True, reindex even if document status is already 'indexed'.

    Returns:
        Dictionary summarizing execution outcome.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning("Job aborted: Document %d does not exist in database.", document_id)
            return {
                "document_id": document_id,
                "status": "not_found",
                "idempotent_skip": False,
            }

        # Idempotency check: Skip duplicate job execution if already successfully indexed
        if not force_reindex and document.status == "indexed" and (document.chunks or 0) > 0:
            logger.info("Job idempotent skip: Document %d is already indexed (%d chunks).", document_id, document.chunks)
            return {
                "document_id": document_id,
                "status": "indexed",
                "chunks": document.chunks,
                "idempotent_skip": True,
            }

        # Execute processing pipeline (parsing, chunking, embedding, vector store upsert)
        process_document_background(document_id=document_id, file_path=file_path)

        # Refresh document state
        db.expire_all()
        doc_updated = db.query(Document).filter(Document.id == document_id).first()

        return {
            "document_id": document_id,
            "status": doc_updated.status if doc_updated else "unknown",
            "chunks": doc_updated.chunks if doc_updated else 0,
            "idempotent_skip": False,
        }
    except Exception as exc:
        logger.error("Job failed for document %d: %s", document_id, exc)
        raise
    finally:
        db.close()
