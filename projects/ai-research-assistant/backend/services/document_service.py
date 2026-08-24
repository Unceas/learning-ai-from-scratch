"""Document Service encapsulating PDF text extraction, chunking, embedding, deduplication, and vector store indexing."""

from typing import Any, Dict, List
from PyPDF2 import PdfReader
from backend.services.chunker import chunk_text
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore
from backend.services.document_hash import calculate_file_hash
from backend.exceptions import EmptyDocumentError
from document_registry import get_document, register_document


class DocumentService:

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

    def extract_text(self, file) -> List[Dict[str, Any]]:
        """Extract text from PDF pages while preserving page numbers."""
        reader = PdfReader(file)
        pages = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({
                    "page": page_number,
                    "text": text.strip()
                })
        return pages

    def index_document(self, file, user_id: str, filename: str = "uploaded_document.pdf") -> Dict[str, Any]:
        """Extract pages, chunk content, generate dense embeddings, and index into ChromaDB with deduplication."""
        file_hash = calculate_file_hash(file)
        existing = get_document(user_id, file_hash)

        if existing:
            return {
                "status": "already_indexed",
                "filename": existing["filename"],
                "chunks": existing["chunks"]
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

        metadatas = []
        ids = []

        for index, chunk in enumerate(chunks):
            metadatas.append({
                "user_id": user_id,
                "document": filename,
                "file_hash": file_hash,
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"]
            })
            ids.append(f"{user_id}_{file_hash}_{index}")

        self.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

        register_document(
            user_id=user_id,
            file_hash=file_hash,
            filename=filename,
            chunks=len(chunks)
        )

        return {
            "status": "indexed",
            "filename": filename,
            "pages": len(pages),
            "chunks": len(chunks)
        }
