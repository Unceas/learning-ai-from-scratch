"""Document API route handling document upload, listing, status, retry, and deletion lifecycle endpoints."""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.responses import (
    ChunkPreviewResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentStatusResponse,
)
from backend.services.authorization import get_owned_document
from backend.services.document_db_service import (
    create_document,
    get_document,
    list_documents,
)
from backend.services.document_db_service import (
    delete_document as delete_document_record,
)
from backend.services.document_hash import calculate_file_hash
from backend.services.document_processor import process_document_background
from backend.services.document_service import DocumentService
from backend.services.rate_limiter import rate_limiter
from backend.services.vector_store import VectorStore
from backend.storage import has_pdf_signature, storage

router = APIRouter()
document_service = DocumentService()
vector_store = VectorStore()


@router.get("", response_model=DocumentListResponse, include_in_schema=False)
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
                "error_message": document.error_message,
                "processing_attempts": document.processing_attempts
            }
            for document in documents
        ]
    }


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    http_request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Upload PDF, register document in processing state, and enqueue background indexing."""
    rate_limiter.enforce(
        http_request,
        scope="upload",
        limit=getattr(settings, "upload_rate_limit_per_minute", 30),
        user_id=user_id,
    )
    raw_filename = file.filename or "uploaded_document.pdf"
    # Defense against directory traversal: sanitize to basename
    filename = Path(raw_filename).name or "uploaded_document.pdf"

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    allowed_mimes = {"application/pdf", "application/x-pdf", "binary/octet-stream"}
    if file.content_type and file.content_type not in allowed_mimes:
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

    if not has_pdf_signature(content):
        raise HTTPException(
            status_code=400,
            detail="File does not have a valid PDF signature."
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

    file_path = storage.save(
        filename,
        content
    )

    if existing and existing.status == "failed":
        existing.status = "processing"
        existing.storage_path = file_path
        existing.error_message = None
        db.commit()
        document = existing
    else:
        document = create_document(
            db=db,
            user_id=user_id,
            file_hash=file_hash,
            filename=filename,
            storage_path=file_path,
            chunks=0,
            status="processing"
        )

    background_tasks.add_task(
        process_document_background,
        document.id
    )

    return {
        "status": "processing",
        "document_id": document.id,
        "filename": document.filename
    }


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse
)
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve document status by ID with strict user-scoped isolation."""
    document = get_owned_document(
        db,
        user_id,
        document_id
    )

    return {
        "id": document.id,
        "filename": document.filename,
        "file_hash": document.file_hash,
        "chunks": document.chunks,
        "status": document.status,
        "error_message": document.error_message,
        "processing_attempts": document.processing_attempts
    }


@router.get(
    "/{document_id}/chunks/{chunk_index}",
    response_model=ChunkPreviewResponse
)
def get_document_chunk(
    document_id: int,
    chunk_index: int,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retrieve an authorized source chunk excerpt and metadata for inspection.
    
    Verifies authenticated user document ownership and 'indexed' status before
    retrieving the chunk from the vector store.
    """
    document = get_owned_document(
        db,
        user_id=user_id,
        document_id=document_id,
        require_indexed=True
    )

    chunk = vector_store.get_chunk(
        document_id=document.id,
        chunk_index=chunk_index,
        user_id=user_id,
        file_hash=document.file_hash
    )
    if not chunk:
        raise HTTPException(
            status_code=404,
            detail=f"Chunk {chunk_index} not found for document {document_id}."
        )

    if chunk.get("document_id") != document_id or chunk.get("chunk_index") != chunk_index:
        raise HTTPException(
            status_code=404,
            detail="Chunk does not match requested document or index."
        )

    return {
        "id": f"S{chunk_index + 1}",
        "document_id": document.id,
        "filename": document.filename,
        "chunk_index": chunk_index,
        "text": chunk.get("text", ""),
        "page": chunk.get("page"),
        "score": chunk.get("score")
    }


@router.post(
    "/{document_id}/retry",
    response_model=DocumentStatusResponse
)
def retry_document(
    http_request: Request,
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Retry ingestion for a failed document belonging to the authenticated user."""
    rate_limiter.enforce(
        http_request,
        scope="retry",
        limit=getattr(settings, "retry_rate_limit_per_minute", 30),
        user_id=user_id,
    )
    document = get_owned_document(
        db,
        user_id,
        document_id
    )

    if document.status != "failed":
        raise HTTPException(
            status_code=400,
            detail="Only failed documents can be retried."
        )

    document.status = "processing"
    document.error_message = None
    db.commit()

    background_tasks.add_task(
        process_document_background,
        document.id
    )

    return {
        "id": document.id,
        "filename": document.filename,
        "file_hash": document.file_hash,
        "chunks": document.chunks,
        "status": document.status,
        "error_message": document.error_message,
        "processing_attempts": document.processing_attempts
    }


@router.delete("/{identifier}")
def delete_document(
    identifier: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Delete document entry from SQLite, purge stored file via storage abstraction, and delete vectors from ChromaDB."""
    document = get_owned_document(db, user_id, identifier)

    if document.storage_path:
        storage.delete(document.storage_path)

    vector_store.delete_by_document_id(document.id)
    vector_store.delete_document(user_id, document.file_hash)
    delete_document_record(db, user_id, document.file_hash)

    # Invalidate retrieval and BM25 caches for user
    try:
        from backend.services.keyword_retriever import bm25_cache
        from backend.services.retrieval_cache import retrieval_cache
        bm25_cache.invalidate_user(user_id)
        retrieval_cache.invalidate_user(user_id)
    except Exception:
        pass

    return {
        "status": "deleted",
        "id": document.id,
        "file_hash": document.file_hash
    }
