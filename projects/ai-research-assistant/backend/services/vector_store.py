"""Vector Store service encapsulating ChromaDB document vector database operations."""

import chromadb
from backend.config import settings


class VectorStore:

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_path)
        self.collection = self.client.get_or_create_collection(name="documents")

    def add_documents(self, texts, embeddings, metadatas, ids):
        """Insert indexed document chunks, embeddings, and metadata into ChromaDB."""
        self.collection.add(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(self, query_embedding, user_id, top_k=5):
        """Search vector database enforced strictly by user_id metadata filter."""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id}
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
