"""Background document processor service for asynchronous PDF ingestion."""

from pathlib import Path
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.services.document_service import process_document
from backend.models import Document


def process_document_background(
    document_id: int,
    file_path: str
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

        document.status = "processing"
        document.error_message = None
        db.commit()

        chunks = process_document(
            file_path=file_path,
            user_id=document.user_id,
            file_hash=document.file_hash,
            filename=document.filename
        )

        document.chunks = len(chunks)
        document.status = "indexed"
        document.error_message = None
        db.commit()

        # Clean up temporary uploaded file after successful processing
        Path(file_path).unlink(missing_ok=True)
    except Exception as exc:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )
        if document:
            document.status = "failed"
            document.error_message = str(exc)
            db.commit()

        # Clean up temporary file on failure as well
        Path(file_path).unlink(missing_ok=True)
    finally:
        db.close()
