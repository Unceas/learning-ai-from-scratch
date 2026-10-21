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

    def get_chunk(
        self,
        document_id: int,
        chunk_index: int,
        user_id: Optional[str] = None,
        file_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chunk for a document by document_id and chunk_index."""
        ids_to_try = [f"{document_id}:{chunk_index}"]
        if user_id and file_hash:
            ids_to_try.append(f"{user_id}_{file_hash}_{chunk_index}")

        res = self.collection.get(
            ids=ids_to_try,
            include=["documents", "metadatas"]
        )
        if not res or not res.get("ids") or len(res["ids"]) == 0:
            where_clause = {
                "$and": [
                    {"document_id": document_id},
                    {"chunk_index": chunk_index}
                ]
            }
            if user_id:
                where_clause = {
                    "$and": [
                        {"user_id": user_id},
                        {"document_id": document_id},
                        {"chunk_index": chunk_index}
                    ]
                }
            try:
                res = self.collection.get(
                    where=where_clause,
                    include=["documents", "metadatas"]
                )
            except Exception:
                res = None

        if not res or not res.get("ids") or len(res["ids"]) == 0:
            return None

        doc_text = res["documents"][0] if res.get("documents") else ""
        metadata = res["metadatas"][0] if res.get("metadatas") else {}

        if user_id and metadata.get("user_id") and metadata.get("user_id") != user_id:
            return None

        meta_doc_id = metadata.get("document_id")
        meta_chunk_idx = metadata.get("chunk_index", metadata.get("chunk_id"))
        if meta_doc_id is not None and meta_doc_id != document_id:
            return None
        if meta_chunk_idx is not None and meta_chunk_idx != chunk_index:
            return None

        return {
            "id": res["ids"][0],
            "document_id": meta_doc_id if meta_doc_id is not None else document_id,
            "filename": metadata.get("filename", metadata.get("document", "Unknown")),
            "chunk_index": meta_chunk_idx if meta_chunk_idx is not None else chunk_index,
            "page": metadata.get("page"),
            "text": doc_text,
            "user_id": metadata.get("user_id")
        }

    def get_user_chunks(
        self,
        user_id: str,
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all indexed chunks belonging to authenticated user and eligible document IDs."""
        if document_ids is not None:
            if not document_ids:
                return []
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

        results = self.collection.get(
            where=where,
            include=["documents", "metadatas"]
        )

        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []
        ids = results.get("ids", []) or []

        chunks = []
        for doc_text, metadata, vec_id in zip(documents, metadatas, ids):
            metadata = metadata or {}
            chunks.append({
                "text": doc_text,
                "document_id": metadata.get("document_id"),
                "filename": metadata.get("filename", metadata.get("document", "Unknown")),
                "chunk_index": metadata.get("chunk_index", metadata.get("chunk_id", 0)),
                "page": metadata.get("page", 1),
                "file_hash": metadata.get("file_hash"),
                "id": vec_id
            })
        return chunks

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

    def health_check(self) -> bool:
        """Verify vector database responsiveness via lightweight collection listing."""
        self.client.list_collections()
        return True

    def close(self) -> None:
        """Close vector store client connection if supported."""
        if hasattr(self.client, "close"):
            try:
                self.client.close()
            except Exception:
                pass


_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Retrieve or create singleton VectorStore instance."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


def reset_vector_store() -> None:
    """Reset singleton instance (useful for test isolation and clean shutdown)."""
    global _vector_store_instance
    if _vector_store_instance is not None:
        _vector_store_instance.close()
        _vector_store_instance = None

