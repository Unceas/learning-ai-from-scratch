"""Embedding Service encapsulating text embedding generation using SentenceTransformer."""

from sentence_transformers import SentenceTransformer
from backend.config import settings


class EmbeddingService:

    def __init__(self):
        self.model = SentenceTransformer(settings.embedding_model)

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
