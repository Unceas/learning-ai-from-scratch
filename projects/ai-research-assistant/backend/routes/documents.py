"""Document API route handling document upload, listing, and deletion lifecycle endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from document_registry import list_documents, remove_document
from backend.services.document_service import DocumentService
from backend.services.vector_store import VectorStore

router = APIRouter()
document_service = DocumentService()
vector_store = VectorStore()


@router.get("/")
def get_documents():
    """List all registered documents for the current user."""
    user_id = "development-user"
    return {
        "documents": list_documents(user_id)
    }


@router.post("/upload")
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

    user_id = "development-user"

    try:
        result = document_service.index_document(
            file.file,
            user_id,
            filename=filename
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Document indexing failed."
        ) from exc


@router.delete("/{file_hash}")
def delete_document(file_hash: str):
    """Delete document entry from registry and purge matching vectors from ChromaDB."""
    user_id = "development-user"
    documents = list_documents(user_id)

    exists = any(doc["file_hash"] == file_hash for doc in documents)
    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    vector_store.delete_document(user_id, file_hash)
    removed = remove_document(user_id, file_hash)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    return {
        "status": "deleted",
        "file_hash": file_hash
    }
