"""Thread-safe, bounded in-memory LRU embedding cache for avoiding redundant vector computations."""

import hashlib
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional


class EmbeddingCache:
    """Bounded, thread-safe Least Recently Used (LRU) cache for embedding vectors.

    Keys are computed using SHA-256 hashes of the text along with the model version
    and namespace, preventing raw text retention in keys and preventing cross-model
    or cross-tenant pollution.
    """

    def __init__(self, max_entries: int = 512):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")

        self.max_entries = max_entries
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._lock = threading.Lock()

        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @staticmethod
    def _key(
        text: str,
        model_version: str,
        namespace: str,
    ) -> str:
        """Generate a secure, namespaced hash key for text and model version."""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"{namespace}:{model_version}:{digest}"

    def get_or_compute(
        self,
        text: str,
        compute: Callable[[str], List[float]],
        *,
        model_version: str,
        namespace: str = "default",
    ) -> List[float]:
        """Retrieve cached embedding or compute, store, and return a fresh vector.

        The compute callback is executed outside the lock to minimize lock contention.
        """
        key = self._key(text, model_version, namespace)

        with self._lock:
            if key in self._cache:
                self.hits += 1
                self._cache.move_to_end(key)
                return self._cache[key].copy()

            self.misses += 1

        # Do expensive embedding work outside the lock.
        vector = list(compute(text))

        with self._lock:
            # Another request may have populated the same key while computing.
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key].copy()

            self._cache[key] = vector.copy()

            if len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
                self.evictions += 1

        return vector.copy()

    def get_or_compute_batch(
        self,
        texts: List[str],
        compute_batch: Callable[[List[str]], List[List[float]]],
        *,
        model_version: str,
        namespace: str = "default",
    ) -> List[List[float]]:
        """Batch-aware embedding lookup and computation with LRU cache integration."""
        if not texts:
            return []

        results: List[Optional[List[float]]] = [None] * len(texts)
        missing_indices: List[int] = []
        missing_texts: List[str] = []

        # 1. Fast cache lookup under lock
        with self._lock:
            for i, text in enumerate(texts):
                key = self._key(text, model_version, namespace)
                if key in self._cache:
                    self.hits += 1
                    self._cache.move_to_end(key)
                    results[i] = self._cache[key].copy()
                else:
                    self.misses += 1
                    missing_indices.append(i)
                    missing_texts.append(text)

        # 2. Compute missing vectors outside lock
        if missing_texts:
            computed_vectors = compute_batch(missing_texts)

            # 3. Insert newly computed vectors under lock
            with self._lock:
                for idx, text, vec in zip(missing_indices, missing_texts, computed_vectors):
                    key = self._key(text, model_version, namespace)
                    vector_copy = list(vec).copy()
                    results[idx] = vector_copy

                    if key not in self._cache:
                        self._cache[key] = vector_copy
                        if len(self._cache) > self.max_entries:
                            self._cache.popitem(last=False)
                            self.evictions += 1
                    else:
                        self._cache.move_to_end(key)

        return [r if r is not None else [] for r in results]

    def clear(self) -> None:
        """Purge all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def reset_stats(self) -> None:
        """Reset telemetry counters without clearing entries."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def stats(self) -> Dict[str, Any]:
        """Return operational cache telemetry metrics."""
        with self._lock:
            total_requests = self.hits + self.misses
            hit_ratio = round(self.hits / total_requests, 4) if total_requests > 0 else 0.0
            return {
                "entries": len(self._cache),
                "max_entries": self.max_entries,
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "hit_ratio": hit_ratio,
            }
