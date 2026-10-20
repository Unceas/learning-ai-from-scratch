from typing import List, Optional
from backend.config import get_settings
from backend.services.embedding_cache import EmbeddingCache

settings = get_settings()

# Global bounded embedding cache instance (512 entries default)
embedding_cache = EmbeddingCache(max_entries=settings.embedding_cache_entries)


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

    def embed_documents(self, texts: list, user_id: Optional[str] = None) -> list:
        """Generate dense vector embeddings for a list of document text chunks via cache."""
        if not texts:
            return []
        namespace = f"user:{user_id}" if user_id else "default"
        model_ver = getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        return embedding_cache.get_or_compute_batch(
            texts,
            compute_batch=lambda missing: self.model.encode(missing).tolist(),
            model_version=model_ver,
            namespace=namespace,
        )

    def embed_query(self, query: str, user_id: Optional[str] = None) -> list:
        """Generate dense vector embedding for a single search query via cache."""
        if not query or not query.strip():
            return []
        namespace = f"user:{user_id}" if user_id else "default"
        model_ver = getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        return embedding_cache.get_or_compute(
            query.strip(),
            compute=lambda q: self.model.encode([q]).tolist()[0],
            model_version=model_ver,
            namespace=namespace,
        )


default_embedding_service = EmbeddingService()


def embed_text(text: str, user_id: str = "default") -> List[float]:
    """Helper to embed single text through the bounded embedding cache."""
    return default_embedding_service.embed_query(text, user_id=user_id)
