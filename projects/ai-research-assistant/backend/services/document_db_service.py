"""Database service for managing document metadata and user ownership in SQLite."""

from typing import Any

from sqlalchemy.orm import Session

from backend.models import Document


def get_document(
    db: Session,
    user_id: str,
    file_hash: str
) -> Document | None:
    """Retrieve document metadata record by user_id and file_hash."""
    return (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.file_hash == file_hash
        )
        .first()
    )


def get_document_by_id(
    db: Session,
    user_id: str,
    document_id: int
) -> Document | None:
    """Retrieve document metadata record by user_id and document_id ensuring strict user isolation."""
    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id
        )
        .first()
    )


def create_document(
    db: Session,
    user_id: str,
    file_hash: str,
    filename: str,
    storage_path: str = "",
    chunks: int = 0,
    status: str = "processing",
    index_version: int = 0
) -> Document:
    """Create and persist a new document metadata record."""
    effective_version = 1 if status == "indexed" and index_version == 0 else index_version
    document = Document(
        user_id=user_id,
        file_hash=file_hash,
        filename=filename,
        storage_path=storage_path,
        chunks=chunks,
        status=status,
        index_version=effective_version,
        error_message=None
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(
    db: Session,
    user_id: str
) -> list[Document]:
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


def get_indexed_document_ids(
    db: Session,
    user_id: str
) -> list[int]:
    """Retrieve list of document IDs that belong to the user and have status == 'indexed'."""
    documents = (
        db.query(Document.id)
        .filter(
            Document.user_id == user_id,
            Document.status == "indexed",
        )
        .all()
    )
    return [document.id for document in documents]


def get_owned_document(
    db: Session,
    user_id: str,
    document_id: int
) -> Document | None:
    """Retrieve an indexed document owned by user_id ensuring status is 'indexed'."""
    return (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.user_id == user_id,
            Document.status == "indexed",
        )
        .first()
    )


def get_indexed_documents(
    db: Session,
    user_id: str
) -> list[Document]:
    """Retrieve full Document records that belong to the user and have status == 'indexed'."""
    return (
        db.query(Document)
        .filter(
            Document.user_id == user_id,
            Document.status == "indexed",
        )
        .order_by(Document.id.asc())
        .all()
    )


def get_eligible_indexed_documents(
    db: Session,
    user_id: str
) -> list[dict[str, Any]]:
    """Retrieve id and index_version for documents eligible for retrieval cache key generation."""
    documents = (
        db.query(Document.id, Document.index_version)
        .filter(
            Document.user_id == user_id,
            Document.status == "indexed",
        )
        .order_by(Document.id.asc())
        .all()
    )
    return [
        {"id": doc.id, "index_version": doc.index_version or 0}
        for doc in documents
    ]

