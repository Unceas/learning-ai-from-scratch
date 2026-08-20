"""Document API route handling document upload and vector indexing endpoints."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.document_service import DocumentService

router = APIRouter()
document_service = DocumentService()


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
