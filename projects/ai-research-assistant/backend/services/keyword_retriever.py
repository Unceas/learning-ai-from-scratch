"""Lexical Keyword Retriever module using BM25Okapi with safe in-memory caching."""

import hashlib
import threading
from collections import OrderedDict
from typing import Any

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

    def __init__(self, chunks: list[Any]):
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
    ) -> list[dict[str, Any]]:
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


class KeywordRetrieverCache:
    """Thread-safe bounded LRU cache for KeywordRetriever instances to avoid index rebuilds on every query."""

    def __init__(self, max_entries: int = 32):
        self.max_entries = max_entries
        self._cache: OrderedDict[str, KeywordRetriever] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def compute_signature(document_ids: list[int | str], chunk_count: int, version: int | str = 0) -> str:
        """Create a deterministic hash signature representing a specific corpus snapshot."""
        sorted_ids = sorted(str(d) for d in document_ids)
        raw = f"{','.join(sorted_ids)}:{chunk_count}:{version}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, user_id: str, signature: str) -> KeywordRetriever | None:
        """Retrieve cached retriever if available."""
        key = f"{user_id}:{signature}"
        with self._lock:
            if key in self._cache:
                self.hits += 1
                self._cache.move_to_end(key)
                return self._cache[key]
            self.misses += 1
            return None

    def put(self, user_id: str, signature: str, retriever: KeywordRetriever) -> None:
        """Store retriever in LRU cache."""
        key = f"{user_id}:{signature}"
        with self._lock:
            self._cache[key] = retriever
            self._cache.move_to_end(key)
            if len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)

    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cached retrievers belonging to a given user."""
        prefix = f"{user_id}:"
        with self._lock:
            keys_to_del = [k for k in self._cache if k.startswith(prefix)]
            for k in keys_to_del:
                del self._cache[k]

    def clear(self) -> None:
        """Purge all entries."""
        with self._lock:
            self._cache.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict[str, Any]:
        """Return cache telemetry."""
        with self._lock:
            total = self.hits + self.misses
            hit_ratio = round(self.hits / total, 4) if total > 0 else 0.0
            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": hit_ratio,
            }


bm25_cache = KeywordRetrieverCache(max_entries=32)


def get_or_build_keyword_retriever(
    user_id: str,
    chunks: list[Any],
    document_ids: list[int | str] | None = None,
    version: int | str = 0,
    use_cache: bool = True,
) -> KeywordRetriever:
    """Get an existing cached KeywordRetriever or build and cache a new one."""
    if not use_cache or not chunks:
        return KeywordRetriever(chunks)

    doc_ids = document_ids or []
    signature = bm25_cache.compute_signature(doc_ids, len(chunks), version)
    cached = bm25_cache.get(user_id, signature)
    if cached is not None:
        return cached

    retriever = KeywordRetriever(chunks)
    bm25_cache.put(user_id, signature, retriever)
    return retriever
