"""Document Service encapsulating PDF text extraction, chunking, embedding, deduplication, and vector store indexing."""

from typing import Any, Dict, List, Optional
from pathlib import Path
from PyPDF2 import PdfReader
from sqlalchemy.orm import Session
from backend.services.chunker import chunk_text
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore
from backend.services.document_hash import calculate_file_hash
from backend.exceptions import EmptyDocumentError
from backend.services.document_db_service import get_document, create_document
from backend.database import SessionLocal
from backend.models import User, Document


def extract_pdf_text_pages(file_or_path) -> List[Dict[str, Any]]:
    """Extract text from PDF pages preserving page numbers."""
    if isinstance(file_or_path, (str, Path)):
        reader = PdfReader(str(file_or_path))
    else:
        reader = PdfReader(file_or_path)

    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text and text.strip():
            pages.append({
                "page": page_number,
                "text": text.strip()
            })
    return pages


def process_document(
    file_path: str,
    user_id: str,
    document_id: Optional[int] = None,
    file_hash: Optional[str] = None,
    filename: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Process physical PDF file in background: extract text, chunk, embed, and index into ChromaDB.
    
    Guarantees idempotency and cleans up stale vectors before upserting.
    """
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found at {file_path}")

    if filename is None:
        filename = path_obj.name

    if file_hash is None:
        with open(file_path, "rb") as f:
            file_hash = calculate_file_hash(f)

    pages = extract_pdf_text_pages(file_path)
    if not pages:
        raise ValueError("No readable text found.")

    chunks = []
    for page in pages:
        page_chunks = chunk_text(page["text"])
        for chunk_id, text in enumerate(page_chunks):
            chunks.append({
                "text": text,
                "page": page["page"],
                "chunk_id": chunk_id
            })

    if not chunks:
        raise ValueError("No readable text found.")

    vector_store = VectorStore()

    # Step 1: Delete old vectors belonging to this document before reindexing
    if document_id is not None:
        vector_store.delete_by_document_id(document_id)

    embedding_service = EmbeddingService()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedding_service.embed_documents(texts)

    metadatas = []
    ids = []

    for index, chunk in enumerate(chunks):
        metadata = {
            "user_id": user_id,
            "file_hash": file_hash,
            "filename": filename,
            "document": filename,
            "page": chunk["page"],
            "chunk_id": chunk["chunk_id"],
            "chunk_index": index
        }
        if document_id is not None:
            metadata["document_id"] = document_id
            vector_id = f"{document_id}:{index}"
        else:
            vector_id = f"{user_id}_{file_hash}_{index}"

        metadatas.append(metadata)
        ids.append(vector_id)

    # Step 2: Upsert current chunks into ChromaDB
    vector_store.upsert_documents(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    return chunks


class DocumentService:

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def extract_text(self, file) -> List[Dict[str, Any]]:
        """Extract text from PDF pages while preserving page numbers."""
        return extract_pdf_text_pages(file)

    def index_document(
        self,
        file,
        user_id: str,
        filename: str = "uploaded_document.pdf",
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Extract pages, chunk content, generate dense embeddings, and index into ChromaDB & SQLite."""
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(id=user_id, password_hash="placeholder_hash")
                db.add(user)
                db.commit()

            file_hash = calculate_file_hash(file)
            existing = get_document(db, user_id, file_hash)

            if existing and existing.status == "indexed":
                return {
                    "status": "already_indexed",
                    "filename": existing.filename,
                    "chunks": existing.chunks
                }

            pages = self.extract_text(file)
            if not pages:
                raise EmptyDocumentError()

            chunks = []
            for page in pages:
                page_chunks = chunk_text(page["text"])
                for chunk_id, text in enumerate(page_chunks):
                    chunks.append({
                        "text": text,
                        "page": page["page"],
                        "chunk_id": chunk_id
                    })

            if not chunks:
                raise EmptyDocumentError()

            texts = [chunk["text"] for chunk in chunks]
            embeddings = self.embedding_service.embed_documents(texts)

            # Ensure document DB record exists to get document_id
            if not existing:
                doc_record = create_document(
                    db=db,
                    user_id=user_id,
                    file_hash=file_hash,
                    filename=filename,
                    chunks=len(chunks),
                    status="indexed"
                )
                document_id = doc_record.id
            else:
                existing.status = "indexed"
                existing.chunks = len(chunks)
                existing.error_message = None
                db.commit()
                document_id = existing.id

            # Clean existing vectors for this document
            self.vector_store.delete_by_document_id(document_id)

            metadatas = []
            ids = []

            for index, chunk in enumerate(chunks):
                metadatas.append({
                    "user_id": user_id,
                    "document_id": document_id,
                    "document": filename,
                    "filename": filename,
                    "file_hash": file_hash,
                    "page": chunk["page"],
                    "chunk_id": chunk["chunk_id"],
                    "chunk_index": index
                })
                ids.append(f"{document_id}:{index}")

            self.vector_store.upsert_documents(
                texts=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            return {
                "status": "indexed",
                "filename": filename,
                "pages": len(pages),
                "chunks": len(chunks)
            }
        finally:
            if close_db:
                db.close()
