"""Database service for managing document metadata and user ownership in SQLite."""

from typing import List, Optional
from sqlalchemy.orm import Session
from backend.models import Document


def get_document(
    db: Session,
    user_id: str,
    file_hash: str
) -> Optional[Document]:
    """Retrieve document metadata record by user_id and file_hash."""
    return (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.file_hash == file_hash
        )
        .first()
    )


def create_document(
    db: Session,
    user_id: str,
    file_hash: str,
    filename: str,
    chunks: int
) -> Document:
    """Create and persist a new document metadata record."""
    document = Document(
        user_id=user_id,
        file_hash=file_hash,
        filename=filename,
        chunks=chunks,
        status="indexed"
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(
    db: Session,
    user_id: str
) -> List[Document]:
    """List all registered document records for a given user."""
    return (
        db.query(Document)
        .filter(Document.user_id == user_id)
        .all()
    )


def delete_document(
    db: Session,
    user_id: str,
    file_hash: str
) -> bool:
    """Delete document metadata record by user_id and file_hash. Returns True if deleted."""
    document = get_document(
        db,
        user_id,
        file_hash
    )
    if not document:
        return False

    db.delete(document)
    db.commit()
    return True
