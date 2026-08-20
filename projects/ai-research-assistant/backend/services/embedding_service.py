"""Embedding Service encapsulating text embedding generation using SentenceTransformer."""

from sentence_transformers import SentenceTransformer


class EmbeddingService:

    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def embed_documents(self, texts: list) -> list:
        """Generate dense vector embeddings for a list of document text chunks."""
        if not texts:
            return []
        return self.model.encode(texts).tolist()

    def embed_query(self, query: str) -> list:
        """Generate dense vector embedding for a single search query."""
        if not query or not query.strip():
            return []
        return self.model.encode([query]).tolist()[0]
