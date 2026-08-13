"""Document API route handling document upload and indexing endpoints."""

from fastapi import APIRouter, UploadFile, File, Form
from typing import Optional
from parser import extract_pages
from retrieval import chunk_pages
import vector_store

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form("default_user")
):
    """Parse PDF/TXT document upload and index into persistent ChromaDB."""
    try:
        pages = extract_pages(file.file)
        chunks = chunk_pages(pages)

        if chunks:
            vector_store.add_document(file.filename, chunks, user_id=user_id)
            status = "indexed"
            chunk_count = len(chunks)
        else:
            status = "empty"
            chunk_count = 0

        return {
            "filename": file.filename,
            "status": status,
            "chunks_indexed": chunk_count,
            "user_id": user_id
        }
    except Exception as e:
        return {
            "filename": file.filename,
            "status": "error",
            "error": str(e)
        }
