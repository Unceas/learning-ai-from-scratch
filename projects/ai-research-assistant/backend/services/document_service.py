"""Document Service encapsulating PDF text extraction, chunking, embedding, and vector store indexing."""

from typing import Any, Dict, List
from PyPDF2 import PdfReader
from backend.services.chunker import chunk_text
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore


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
        """Extract pages, chunk content, generate dense embeddings, and index into ChromaDB."""
        pages = self.extract_text(file)
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
            return {
                "status": "empty",
                "chunks": 0
            }

        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_service.embed_documents(texts)

        metadatas = []
        ids = []

        for index, chunk in enumerate(chunks):
            metadatas.append({
                "user_id": user_id,
                "document": filename,
                "page": chunk["page"],
                "chunk_id": chunk["chunk_id"]
            })
            ids.append(f"{user_id}_{filename}_{index}")

        self.vector_store.add_documents(
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
