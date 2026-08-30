"""Document API route handling document upload, listing, and deletion lifecycle endpoints."""

from pathlib import Path
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from backend.services.document_service import DocumentService
from backend.services.vector_store import VectorStore
from backend.services.document_db_service import (
    get_document,
    list_documents,
    create_document,
    delete_document as delete_document_record
)
from backend.services.document_processor import process_document_background
from backend.services.document_hash import calculate_file_hash
from backend.database import get_db
from backend.schemas.responses import DocumentResponse, DocumentListResponse
from backend.exceptions import DocumentNotFoundError
from backend.dependencies import get_current_user
from backend.config import settings

router = APIRouter()
document_service = DocumentService()
vector_store = VectorStore()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


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
                "id": document.id,
                "file_hash": document.file_hash,
                "filename": document.filename,
                "chunks": document.chunks,
                "status": document.status,
                "error_message": document.error_message
            }
            for document in documents
        ]
    }


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Upload PDF, register document in processing state, and enqueue background indexing."""
    filename = file.filename or "uploaded_document.pdf"

    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    content = await file.read()
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail="File is too large."
        )

    file_hash = calculate_file_hash(content)

    existing = get_document(
        db,
        user_id,
        file_hash
    )

    if existing and existing.status in ["indexed", "processing"]:
        return {
            "status": existing.status,
            "document_id": existing.id,
            "filename": existing.filename,
            "chunks": existing.chunks,
            "error_message": existing.error_message
        }

    file_path = UPLOAD_DIR / f"{uuid.uuid4()}_{filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    if existing and existing.status == "failed":
        existing.status = "processing"
        existing.error_message = None
        db.commit()
        document = existing
    else:
        document = create_document(
            db=db,
            user_id=user_id,
            file_hash=file_hash,
            filename=filename,
            chunks=0,
            status="processing"
        )

    background_tasks.add_task(
        process_document_background,
        document.id,
        str(file_path)
    )

    return {
        "status": "processing",
        "document_id": document.id,
        "filename": document.filename
    }


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
