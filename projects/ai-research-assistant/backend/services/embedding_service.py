from typing import Optional
from backend.config import settings


class EmbeddingService:
    _model = None

    def __init__(self):
        pass

    @property
    def model(self):
        """Lazy-load SentenceTransformer model on first actual use."""
        if EmbeddingService._model is None:
            from sentence_transformers import SentenceTransformer
            EmbeddingService._model = SentenceTransformer(settings.embedding_model)
        return EmbeddingService._model

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
