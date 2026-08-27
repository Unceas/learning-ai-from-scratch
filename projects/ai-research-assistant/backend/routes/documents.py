"""Document API route handling document upload, listing, and deletion lifecycle endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.services.document_service import DocumentService
from backend.services.vector_store import VectorStore
from backend.services.document_db_service import (
    get_document,
    list_documents,
    delete_document as delete_document_record
)
from backend.database import get_db
from backend.schemas.responses import DocumentResponse, DocumentListResponse
from backend.exceptions import DocumentNotFoundError
from backend.dependencies import get_current_user
from backend.config import settings

router = APIRouter()
document_service = DocumentService()
vector_store = VectorStore()


@router.get("/", response_model=DocumentListResponse)
def get_documents(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """List all registered documents for the authenticated user from SQLite database."""
    documents = list_documents(db, user_id)
    return {
        "documents": [
            {
                "file_hash": document.file_hash,
                "filename": document.filename,
                "chunks": document.chunks,
                "status": document.status
            }
            for document in documents
        ]
    }


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Upload and index PDF document vectors with metadata stored in SQLite."""
    filename = file.filename or "uploaded_document.pdf"

    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    max_file_size = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_file_size:
        raise HTTPException(
            status_code=413,
            detail="File is too large."
        )
    await file.seek(0)

    result = document_service.index_document(
        file.file,
        user_id,
        filename=filename,
        db=db
    )
    return result


@router.delete("/{file_hash}")
def delete_document(
    file_hash: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Delete document entry from SQLite and purge matching vectors from ChromaDB."""
    document = get_document(db, user_id, file_hash)
    if not document:
        raise DocumentNotFoundError()

    vector_store.delete_document(user_id, file_hash)
    delete_document_record(db, user_id, file_hash)

    return {
        "status": "deleted",
        "file_hash": file_hash
    }
