"""Lexical Keyword Retriever module using BM25Okapi."""

from typing import Any, Dict, List
from rank_bm25 import BM25Okapi


def _extract_chunk_text(chunk: Any) -> str:
    """Extract plain text string from chunk object or dictionary."""
    if hasattr(chunk, "text"):
        return getattr(chunk, "text", "") or ""
    if isinstance(chunk, dict):
        return chunk.get("text", chunk.get("content", "")) or ""
    return str(chunk or "")


class KeywordRetriever:
    """Lexical keyword retriever powered by BM25Okapi over restricted document chunks."""

    def __init__(self, chunks: List[Any]):
        """Initialize BM25 index over provided chunk corpus.

        Args:
            chunks: List of chunk dictionaries or RetrievedChunk objects strictly restricted
                    to an authenticated user's indexed documents.
        """
        self.chunks = list(chunks) if chunks else []
        self.tokenized_corpus = [
            _extract_chunk_text(chunk).lower().split()
            for chunk in self.chunks
        ]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filter_zero: bool = True
    ) -> List[Dict[str, Any]]:
        """Retrieve top_k matching chunks for query using BM25 scoring.

        Args:
            query: User search query.
            top_k: Maximum number of ranked chunks to return.
            filter_zero: If True, exclude chunks with BM25 score of 0.0.

        Returns:
            List of dictionaries: [{"chunk": chunk, "score": float(score)}]
        """
        if not self.bm25 or not query or not query.strip() or top_k <= 0:
            return []

        query_tokens = query.lower().split()
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )

        results = []
        for i in ranked_indices:
            score_val = float(scores[i])
            if filter_zero and score_val <= 0.0:
                continue
            results.append({
                "chunk": self.chunks[i],
                "score": score_val,
            })
            if len(results) >= top_k:
                break

        return results
