"""Hybrid Retriever service combining dense vector search and BM25 lexical search with RRF."""

from typing import Any, Callable, Dict, List, Optional, Union
from backend.services.rank_fusion import reciprocal_rank_fusion


class HybridRetriever:
    """Coordinates hybrid retrieval across dense semantic and BM25 lexical retrievers."""

    def __init__(
        self,
        dense_retriever: Any,
        keyword_retriever: Any,
        rrf_k: int = 60
    ):
        """Initialize with dense and keyword retrievers.

        Args:
            dense_retriever: Object with a .retrieve(query, top_k) method or a callable.
            keyword_retriever: KeywordRetriever instance with .retrieve(query, top_k) or a callable.
            rrf_k: Smoothing constant for reciprocal rank fusion.
        """
        self.dense_retriever = dense_retriever
        self.keyword_retriever = keyword_retriever
        self.rrf_k = rrf_k

    def _call_retriever(self, retriever: Any, query: str, top_k: int) -> List[Any]:
        """Invoke retriever whether implemented as an object with .retrieve or a direct callable."""
        if hasattr(retriever, "retrieve"):
            return retriever.retrieve(query, top_k=top_k)
        if callable(retriever):
            return retriever(query, top_k=top_k)
        return []

    def retrieve(
        self,
        query: str,
        dense_k: int = 10,
        keyword_k: int = 10,
        final_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Retrieve and fuse candidate chunks using dense semantic and BM25 lexical search.

        Args:
            query: User search query.
            dense_k: Number of candidates to retrieve from dense vector retriever.
            keyword_k: Number of candidates to retrieve from keyword retriever.
            final_k: Maximum number of fused chunks to return.

        Returns:
            List of fused results: [{"chunk": chunk, "score": score}, ...]
        """
        if not query or not query.strip():
            return []

        dense_results = self._call_retriever(self.dense_retriever, query, dense_k)
        keyword_results = self._call_retriever(self.keyword_retriever, query, keyword_k)

        fused = reciprocal_rank_fusion(
            [
                dense_results,
                keyword_results,
            ],
            k=self.rrf_k
        )

        return fused[:final_k]
