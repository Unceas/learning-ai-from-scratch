"""Two-stage retrieval reranking service.

Provides an abstract Reranker interface and a CrossEncoder implementation to score
(query, passage) pairs together for high-precision passage re-ranking.
Preserves both vector_score and reranker_score on candidate chunks.
"""

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Union

from backend.config import settings
from backend.services.rag_context import RetrievedChunk

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Abstract base class contract for passage rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: List[Union[RetrievedChunk, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank candidate chunks according to their relevance to the query.

        Args:
            query: User search query.
            chunks: Candidate chunks retrieved from vector search.
            top_k: Maximum number of reranked chunks to return.

        Returns:
            List of ranked chunk dictionaries sorted descending by relevance.
        """
        pass


class CrossEncoderReranker(Reranker):
    """Cross-encoder based reranker that jointly encodes (query, passage) pairs."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.reranker_model_name
        self._model = None

    @property
    def model(self):
        """Lazy load the CrossEncoder model instance."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
                logger.info("Loaded CrossEncoder reranker model: %s", self.model_name)
            except Exception as e:
                logger.warning(
                    "Failed to load CrossEncoder model '%s': %s. Falling back to passthrough.",
                    self.model_name, e
                )
                self._model = False
        return self._model if self._model is not False else None

    def rerank(
        self,
        query: str,
        chunks: List[Union[RetrievedChunk, Dict[str, Any]]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Jointly score (query, chunk) pairs and return top_k reranked results."""
        if not chunks or not query or not query.strip():
            return []

        # Extract text and preserve original metadata
        prepared_chunks: List[Dict[str, Any]] = []
        for chunk in chunks:
            if isinstance(chunk, RetrievedChunk):
                orig_score = float(chunk.score)
                v_score = chunk.vector_score if chunk.vector_score is not None else orig_score
                c_dict = {
                    "text": chunk.text,
                    "score": orig_score,
                    "vector_score": v_score,
                    "reranker_score": None,
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "chunk_index": chunk.chunk_index,
                    "page": chunk.page,
                    "file_hash": chunk.file_hash
                }
            elif isinstance(chunk, dict):
                orig_score = float(chunk.get("score", 0.0))
                v_score = float(chunk.get("vector_score", orig_score))
                c_dict = {
                    "text": chunk.get("text", ""),
                    "score": orig_score,
                    "vector_score": v_score,
                    "reranker_score": chunk.get("reranker_score"),
                    "document_id": chunk.get("document_id"),
                    "filename": chunk.get("filename") or chunk.get("document") or "Unknown",
                    "chunk_index": chunk.get("chunk_index", chunk.get("chunk_id", chunk.get("chunk", 0))),
                    "page": chunk.get("page", 1),
                    "file_hash": chunk.get("file_hash")
                }
            else:
                c_dict = {
                    "text": str(chunk),
                    "score": 0.0,
                    "vector_score": 0.0,
                    "reranker_score": None,
                    "document_id": None,
                    "filename": "Unknown",
                    "chunk_index": 0,
                    "page": 1,
                    "file_hash": None
                }
            prepared_chunks.append(c_dict)

        cross_model = self.model
        if cross_model is None:
            # Model unavailable: retain original vector scores and order
            return prepared_chunks[:top_k]

        pairs = [(query, c["text"]) for c in prepared_chunks]
        try:
            raw_scores = cross_model.predict(pairs)
            ranked_pairs = sorted(
                zip(prepared_chunks, raw_scores),
                key=lambda x: float(x[1]),
                reverse=True
            )

            reranked_results = []
            for chunk_dict, rerank_score in ranked_pairs[:top_k]:
                score_val = round(float(rerank_score), 4)
                updated = dict(chunk_dict)
                updated["reranker_score"] = score_val
                # Primary ranking score becomes the reranker score
                updated["score"] = score_val
                reranked_results.append(updated)

            return reranked_results
        except Exception as e:
            logger.error("Error during cross-encoder prediction: %s", e)
            return prepared_chunks[:top_k]


_reranker_singleton: Optional[Reranker] = None


def get_reranker(model_name: Optional[str] = None) -> Reranker:
    """Retrieve the singleton instance of the configured Reranker."""
    global _reranker_singleton
    if _reranker_singleton is None:
        _reranker_singleton = CrossEncoderReranker(model_name)
    return _reranker_singleton
