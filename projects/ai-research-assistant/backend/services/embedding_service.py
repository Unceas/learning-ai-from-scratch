
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
        """Lazy-load SentenceTransformer model on first actual use (singleton)."""
        if EmbeddingService._model is None:
            from sentence_transformers import SentenceTransformer
            EmbeddingService._model = SentenceTransformer(settings.embedding_model)
        return EmbeddingService._model

    def embed_documents(self, texts: list[str], user_id: str | None = None) -> list[list[float]]:
        """Generate dense vector embeddings for a list of document text chunks via cache and configurable batching."""
        if not texts:
            return []
        namespace = f"user:{user_id}" if user_id else "default"
        model_ver = getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        batch_size = max(1, getattr(settings, "embedding_batch_size", 32))

        def _batched_encode(missing: list[str]) -> list[list[float]]:
            if not missing:
                return []
            all_vectors: list[list[float]] = []
            for i in range(0, len(missing), batch_size):
                sub_batch = missing[i:i + batch_size]
                encoded = self.model.encode(sub_batch, batch_size=len(sub_batch))
                if hasattr(encoded, "tolist"):
                    encoded = encoded.tolist()
                all_vectors.extend(encoded)
            return all_vectors

        return embedding_cache.get_or_compute_batch(
            texts,
            compute_batch=_batched_encode,
            model_version=model_ver,
            namespace=namespace,
        )

    def embed_query(self, query: str, user_id: str | None = None) -> list[float]:
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


def embed_text(text: str, user_id: str = "default") -> list[float]:
    """Helper to embed single text through the bounded embedding cache."""
    return default_embedding_service.embed_query(text, user_id=user_id)
