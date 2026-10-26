"""Thread-safe bounded in-memory cache for candidate retrieval results with safe invalidation."""

import hashlib
import json
import threading
from collections import OrderedDict
from copy import deepcopy
from typing import Any


class RetrievalCache:
    """Bounded, thread-safe Least Recently Used (LRU) cache for retrieval candidates.

    Cache keys are computed using deterministic SHA-256 digests over:
      - Authenticated user ID
      - Sorted eligible document IDs and their index_versions
      - Exact query string
      - Retrieval configuration (strategy, candidate count, embedding model)

    This ensures no cross-user leakage, automatic invalidation on reindexing or deletion,
    and returns independent deep copies to prevent caller mutations.
    """

    def __init__(self, max_entries: int = 256):
        if max_entries < 1:
            raise ValueError("max_entries must be positive")

        self.max_entries = max_entries
        self._cache: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

        self.hits = 0
        self.misses = 0
        self.evictions = 0

    @staticmethod
    def make_key(
        *,
        user_id: str,
        eligible_documents: list[dict[str, Any]],
        query: str,
        retrieval_config: dict[str, Any],
    ) -> str:
        """Construct a deterministic SHA-256 hash key for a retrieval request."""
        payload = {
            "user_id": user_id,
            "eligible_documents": sorted(
                eligible_documents,
                key=lambda item: item["id"],
            ),
            "query": query,
            "retrieval_config": retrieval_config,
        }

        serialized = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def get(self, key: str) -> list[dict[str, Any]] | None:
        """Retrieve deep-copied candidates from cache on hit, or None on miss."""
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None

            self.hits += 1
            self._cache.move_to_end(key)
            return deepcopy(self._cache[key])

    def set(self, key: str, candidates: list[dict[str, Any]]) -> None:
        """Store deep-copied candidates into LRU cache with capacity enforcement."""
        with self._lock:
            self._cache[key] = deepcopy(candidates)
            self._cache.move_to_end(key)

            if len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)
                self.evictions += 1

    def clear(self) -> None:
        """Purge all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def reset_stats(self) -> None:
        """Reset telemetry counters without clearing cached entries."""
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    def stats(self) -> dict[str, Any]:
        """Return operational telemetry metrics."""
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


from backend.config import get_settings

_settings = get_settings()
retrieval_cache = RetrievalCache(max_entries=_settings.retrieval_cache_entries)
