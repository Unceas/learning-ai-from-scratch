"""Bounded in-memory and distributed Redis cache implementations for candidate retrieval results with safe invalidation."""

import hashlib
import json
import logging
import threading
from collections import OrderedDict
from copy import deepcopy
from typing import Any

from backend.config import get_settings

logger = logging.getLogger("research_assistant.cache")


class RetrievalCache:
    """Bounded, thread-safe Least Recently Used (LRU) in-memory cache for retrieval candidates.

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
        self._key_user_map: dict[str, str] = {}
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

    def set(self, key: str, candidates: list[dict[str, Any]], user_id: str | None = None) -> None:
        """Store deep-copied candidates into LRU cache with capacity enforcement."""
        with self._lock:
            self._cache[key] = deepcopy(candidates)
            self._cache.move_to_end(key)
            if user_id:
                self._key_user_map[key] = user_id

            if len(self._cache) > self.max_entries:
                evicted_key, _ = self._cache.popitem(last=False)
                self._key_user_map.pop(evicted_key, None)
                self.evictions += 1

    def invalidate_user(self, user_id: str) -> None:
        """Purge all cached retrieval entries associated with a specific user."""
        with self._lock:
            keys_to_del = [k for k, u in self._key_user_map.items() if u == user_id]
            for k in keys_to_del:
                self._cache.pop(k, None)
                self._key_user_map.pop(k, None)

    def clear(self) -> None:
        """Purge all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._key_user_map.clear()

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
                "backend": "in_memory",
            }


class RedisRetrievalCache:
    """Distributed Redis-backed retrieval cache with TTL, JSON serialization, and tenant isolation."""

    def __init__(
        self,
        redis_url: str | None = None,
        default_ttl: int = 300,
        client: Any = None,
    ):
        self.default_ttl = default_ttl
        self._client = client
        self.hits = 0
        self.misses = 0

        if self._client is None and redis_url:
            try:
                from redis import Redis
                self._client = Redis.from_url(redis_url, decode_responses=True)
            except Exception as exc:
                logger.warning("Failed connecting to Redis for retrieval cache: %s", exc)
                self._client = None

    @staticmethod
    def make_key(
        *,
        user_id: str,
        eligible_documents: list[dict[str, Any]],
        query: str,
        retrieval_config: dict[str, Any],
    ) -> str:
        return RetrievalCache.make_key(
            user_id=user_id,
            eligible_documents=eligible_documents,
            query=query,
            retrieval_config=retrieval_config,
        )

    def get(self, key: str) -> list[dict[str, Any]] | None:
        """Fetch cached candidates from Redis."""
        if self._client is None:
            self.misses += 1
            return None
        try:
            raw = self._client.get(f"retrieval:{key}")
            if raw is None:
                self.misses += 1
                return None
            self.hits += 1
            return json.loads(raw)
        except Exception as exc:
            logger.debug("Redis retrieval cache get error: %s", exc)
            self.misses += 1
            return None

    def set(
        self,
        key: str,
        candidates: list[dict[str, Any]],
        ttl: int | None = None,
        user_id: str | None = None,
    ) -> None:
        """Store candidates in Redis with TTL expiration."""
        if self._client is None:
            return
        try:
            effective_ttl = ttl or self.default_ttl
            serialized = json.dumps(candidates)
            self._client.setex(f"retrieval:{key}", effective_ttl, serialized)
            if user_id:
                # Track user's keys in a set for tenant invalidation
                self._client.sadd(f"user_keys:{user_id}", key)
                self._client.expire(f"user_keys:{user_id}", effective_ttl * 2)
        except Exception as exc:
            logger.debug("Redis retrieval cache set error: %s", exc)

    def invalidate_user(self, user_id: str) -> None:
        """Invalidate all cached queries for a user upon corpus modification or deletion."""
        if self._client is None:
            return
        try:
            user_keys_set = f"user_keys:{user_id}"
            keys = self._client.smembers(user_keys_set)
            if keys:
                redis_keys = [f"retrieval:{k}" for k in keys]
                self._client.delete(*redis_keys)
                self._client.delete(user_keys_set)
        except Exception as exc:
            logger.debug("Redis user cache invalidation error: %s", exc)

    def clear(self) -> None:
        """Purge all retrieval keys from Redis."""
        if self._client is None:
            return
        try:
            keys = self._client.keys("retrieval:*")
            if keys:
                self._client.delete(*keys)
            self.hits = 0
            self.misses = 0
        except Exception:
            pass

    def stats(self) -> dict[str, Any]:
        """Return operational telemetry metrics."""
        total = self.hits + self.misses
        hit_ratio = round(self.hits / total, 4) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": hit_ratio,
            "backend": "redis",
        }


_settings = get_settings()
retrieval_cache = RetrievalCache(max_entries=_settings.retrieval_cache_entries)


def get_retrieval_cache():
    """Factory returning distributed RedisRetrievalCache if enabled, otherwise in-memory RetrievalCache."""
    settings = get_settings()
    if settings.distributed_cache_enabled and settings.redis_url:
        return RedisRetrievalCache(
            redis_url=settings.redis_url,
            default_ttl=settings.distributed_cache_ttl,
        )
    return retrieval_cache
