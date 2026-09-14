"""Vector Store service encapsulating ChromaDB document vector database operations."""

from typing import Any, Dict, List, Optional
import chromadb
from backend.config import settings


class VectorStore:

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.client.get_or_create_collection(name="documents")

    def upsert_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Upsert indexed document chunks, embeddings, and metadata into ChromaDB idempotently."""
        if not ids:
            return
        self.collection.upsert(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """Add documents using upsert to guarantee idempotency across indexing attempts."""
        self.upsert_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def delete_by_document_id(self, document_id: int) -> None:
        """Delete all document chunks from ChromaDB for a specific document_id."""
        self.collection.delete(
            where={"document_id": document_id}
        )

    def count_by_document_id(self, document_id: int) -> int:
        """Count total vectors indexed for a specific document_id."""
        results = self.collection.get(
            where={"document_id": document_id}
        )
        return len(results["ids"]) if results and "ids" in results else 0

    def get_by_document_id(self, document_id: int) -> Dict[str, Any]:
        """Retrieve all vector records for a specific document_id."""
        return self.collection.get(
            where={"document_id": document_id}
        )

    def search(
        self,
        query_embedding: List[float],
        user_id: str,
        document_ids: Optional[List[int]] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Search vector database enforced strictly by user_id and optional document_id filter."""
        if document_ids is not None:
            if not document_ids:
                return {
                    "ids": [[]],
                    "documents": [[]],
                    "metadatas": [[]],
                    "distances": [[]]
                }
            if len(document_ids) == 1:
                doc_filter = {"document_id": document_ids[0]}
            else:
                doc_filter = {"document_id": {"$in": document_ids}}

            where = {
                "$and": [
                    {"user_id": user_id},
                    doc_filter
                ]
            }
        else:
            where = {"user_id": user_id}

        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

    def delete_document(self, user_id, file_hash):
        """Delete all document chunks from ChromaDB for given user_id and file_hash."""
        self.collection.delete(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"file_hash": file_hash}
                ]
            }
        )
