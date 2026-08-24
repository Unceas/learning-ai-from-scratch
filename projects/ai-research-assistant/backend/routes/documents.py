"""Document API route handling document upload, listing, and deletion lifecycle endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from document_registry import list_documents, remove_document
from backend.services.document_service import DocumentService
from backend.services.vector_store import VectorStore
from backend.schemas.responses import DocumentResponse, DocumentListResponse
from backend.exceptions import DocumentNotFoundError
from backend.config import settings

router = APIRouter()
document_service = DocumentService()
vector_store = VectorStore()


@router.get("/", response_model=DocumentListResponse)
def get_documents():
    """List all registered documents for the current user."""
    user_id = "development-user"
    return {
        "documents": list_documents(user_id)
    }


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...)
):
    """Upload and index PDF document vectors via DocumentService."""
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

    user_id = "development-user"

    result = document_service.index_document(
        file.file,
        user_id,
        filename=filename
    )
    return result


@router.delete("/{file_hash}")
def delete_document(file_hash: str):
    """Delete document entry from registry and purge matching vectors from ChromaDB."""
    user_id = "development-user"
    documents = list_documents(user_id)

    exists = any(doc["file_hash"] == file_hash for doc in documents)
    if not exists:
        raise DocumentNotFoundError()

    vector_store.delete_document(user_id, file_hash)
    removed = remove_document(user_id, file_hash)

    if not removed:
        raise DocumentNotFoundError()

    return {
        "status": "deleted",
        "file_hash": file_hash
    }
