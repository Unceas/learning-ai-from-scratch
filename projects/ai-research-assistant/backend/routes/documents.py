"""Document API route handling document upload, extraction, chunking, and ChromaDB vector indexing endpoints."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from backend.services.document_service import DocumentService
from backend.services.chunker import chunk_text
import vector_store

router = APIRouter()
document_service = DocumentService()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form("development-user")
):
    """Parse PDF document, extract text by page, chunk content, and index vectors in ChromaDB."""
    filename = file.filename or "uploaded_document.pdf"

    if not filename.lower().endswith((".pdf", ".txt")) and file.content_type not in ["application/pdf", "text/plain"]:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported."
        )

    try:
        if filename.lower().endswith(".pdf") or file.content_type == "application/pdf":
            pages = document_service.extract_text(file.file)
        else:
            raw_text = (await file.read()).decode("utf-8", errors="ignore")
            pages = [{"page": 1, "text": raw_text.strip()}] if raw_text.strip() else []

        if not pages:
            raise HTTPException(
                status_code=400,
                detail="No readable text found."
            )

        all_chunks = []
        for page in pages:
            text_chunks = chunk_text(page["text"])
            for index, chunk in enumerate(text_chunks):
                all_chunks.append({
                    "text": chunk,
                    "page": page["page"],
                    "chunk": index
                })

        vector_store.add_document(filename, all_chunks, user_id=user_id)

        return {
            "filename": filename,
            "pages": len(pages),
            "chunks_indexed": len(all_chunks),
            "status": "extracted",
            "user_id": user_id
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Document processing failed."
        ) from exc
