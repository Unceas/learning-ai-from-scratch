"""Background document processor service for asynchronous PDF ingestion."""

import threading

from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Document
from backend.services.document_service import process_document
from backend.services.vector_store import VectorStore

_max_ingestions = getattr(settings, "max_concurrent_ingestions", 2)
ingestion_semaphore = threading.BoundedSemaphore(max(1, _max_ingestions))


def process_document_background(
    document_id: int,
    file_path: str | None = None
):
    """Execute PDF parsing, chunking, embedding generation, and ChromaDB indexing in background worker."""
    db: Session = SessionLocal()
    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )
        if not document:
            return

        document.processing_attempts += 1
        document.status = "processing"
        document.error_message = None
        db.commit()

        effective_file_path = file_path or document.storage_path

        with ingestion_semaphore:
            chunks = process_document(
                file_path=effective_file_path,
                user_id=document.user_id,
                document_id=document.id,
                file_hash=document.file_hash,
                filename=document.filename
            )

        # Re-verify document still exists in database and was not deleted concurrently
        doc_check = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )
        if not doc_check:
            # Document was deleted concurrently while indexing was in progress.
            # Clean up any newly written vectors and exit without resurrecting.
            try:
                vector_store = VectorStore()
                vector_store.delete_by_document_id(document_id)
            except Exception:
                pass
            return

        doc_check.chunks = len(chunks)
        doc_check.status = "indexed"
        doc_check.index_version = (doc_check.index_version or 0) + 1
        doc_check.error_message = None
        db.commit()

        # Invalidate BM25 and retrieval caches for user on corpus index update
        try:
            from backend.services.keyword_retriever import bm25_cache
            from backend.services.retrieval_cache import retrieval_cache
            bm25_cache.invalidate_user(doc_check.user_id)
            retrieval_cache.invalidate_user(doc_check.user_id)
        except Exception:
            pass
    except Exception as exc:
        db.rollback()

        # Clean up partial vectors on failure so Chroma doesn't retain unsearchable/corrupted chunks
        try:
            vector_store = VectorStore()
            vector_store.delete_by_document_id(document_id)
        except Exception:
            pass

        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )
        if document:
            document.status = "failed"
            safe_err = str(exc)
            if len(safe_err) > 200:
                safe_err = safe_err[:200] + "..."
            document.error_message = safe_err
            db.commit()
    finally:
        db.close()
