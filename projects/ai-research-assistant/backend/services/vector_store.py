"""Vector Store service encapsulating ChromaDB document vector database operations."""

import chromadb


class VectorStore:

    def __init__(self):
        self.client = chromadb.PersistentClient(path="./document_db")
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
