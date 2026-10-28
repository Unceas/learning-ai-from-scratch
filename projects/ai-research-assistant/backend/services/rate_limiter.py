"""In-memory thread-safe rate limiter with trusted proxy detection and sliding window throttling."""

import logging
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from backend.config import settings

logger = logging.getLogger(__name__)


def get_client_ip(
    request: Request,
    trusted_proxies: list[str] | set[str] | None = None,
) -> str:
    """Extract client IP address safely, only trusting X-Forwarded-For from trusted proxies.

    Prevents IP spoofing: if client.host is untrusted, forwarded headers are ignored.
    """
    if trusted_proxies is None:
        trusted_proxies = getattr(settings, "trusted_proxies", ["127.0.0.1", "::1"])
    trusted_set = set(trusted_proxies)

    direct_ip = request.client.host if request.client else "127.0.0.1"

    if direct_ip in trusted_set:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First non-empty entry in comma-separated chain is the client IP
            candidates = [p.strip() for p in forwarded.split(",") if p.strip()]
            if candidates:
                return candidates[0]

    return direct_ip


class RateLimiter:
    """Thread-safe sliding-window rate limiter supporting per-user and per-IP scoping."""

    def __init__(self):
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """Check if request is allowed under sliding window limit.

        Returns:
            (is_allowed: bool, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds

        with self._lock:
            # Purge timestamps older than the active window
            timestamps = [t for t in self._history[key] if t > window_start]
            self._history[key] = timestamps

            if len(timestamps) >= limit:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(oldest_in_window + window_seconds - now))
                return False, retry_after

            # Record current request timestamp
            self._history[key].append(now)
            return True, 0

    def enforce(
        self,
        request: Request,
        scope: str,
        limit: int,
        window_seconds: int = 60,
        user_id: str | None = None,
    ) -> None:
        """Enforce rate limit, raising HTTP 429 Too Many Requests if exceeded."""
        if not getattr(settings, "rate_limit_enabled", True):
            return

        client_ip = get_client_ip(request)
        if user_id:
            key = f"user:{scope}:{user_id}"
        else:
            key = f"ip:{scope}:{client_ip}"

        allowed, retry_after = self.check_limit(key, limit=limit, window_seconds=window_seconds)
        if not allowed:
            logger.warning(
                "Rate limit exceeded for key=%s scope=%s limit=%d window=%ds retry_after=%ds",
                key,
                scope,
                limit,
                window_seconds,
                retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {scope}. Please wait {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

    def reset(self) -> None:
        """Reset all rate limiting buckets (useful for test isolation)."""
        with self._lock:
            self._history.clear()


rate_limiter = RateLimiter()
