"""Background document processor service for asynchronous PDF ingestion."""

from typing import Optional
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.services.document_service import process_document
from backend.services.vector_store import VectorStore
from backend.models import Document


def process_document_background(
    document_id: int,
    file_path: Optional[str] = None
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

        chunks = process_document(
            file_path=effective_file_path,
            user_id=document.user_id,
            document_id=document.id,
            file_hash=document.file_hash,
            filename=document.filename
        )

        document.chunks = len(chunks)
        document.status = "indexed"
        document.error_message = None
        db.commit()
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
            document.error_message = str(exc)
            db.commit()
    finally:
        db.close()
