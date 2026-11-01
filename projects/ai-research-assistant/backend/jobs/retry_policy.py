"""Retry policy and failure classification for distributed background tasks."""

import random
import time


class RetryPolicy:
    """Configurable exponential backoff retry policy with jitter and failure classification."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.initial_delay_seconds = initial_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    @staticmethod
    def is_transient_error(exc: Exception) -> bool:
        """Classify whether an exception is transient (retryable) or permanent (fatal).

        Transient failures:
            - Network connection timeouts / resets
            - HTTP 429 Too Many Requests / Resource Exhausted
            - HTTP 503 Service Unavailable / 502 Bad Gateway
            - Redis broker temporary disconnections
            - Database lock timeouts

        Permanent failures:
            - Corrupted or invalid PDF signatures (magic byte mismatches)
            - Authentication / Invalid API key credentials
            - Missing files / 404 Not Found
            - Schema validation errors
        """
        err_msg = str(exc).lower()
        exc_type = type(exc).__name__.lower()

        # Permanent fatal errors
        permanent_keywords = [
            "invalid pdf",
            "invalid api key",
            "unsupported file format",
            "permission denied",
            "not found",
            "filenotfounderror",
            "valueerror",
        ]
        if any(kw in err_msg or kw in exc_type for kw in permanent_keywords):
            return False

        # Built-in transient exceptions (ConnectionResetError, ConnectionRefusedError, TimeoutError, etc.)
        if isinstance(exc, (ConnectionError, TimeoutError)):
            return True

        # Transient retryable errors
        transient_keywords = [
            "timeout",
            "timeouterror",
            "connection error",
            "connection refused",
            "connection reset",
            "connectionreseterror",
            "connectionrefusederror",
            "429",
            "resource exhausted",
            "rate limit",
            "503",
            "service unavailable",
            "502",
            "bad gateway",
            "broker disconnected",
            "database locked",
            "lock wait timeout",
        ]
        return any(kw in err_msg or kw in exc_type for kw in transient_keywords)

    def should_retry(self, exc: Exception, attempt: int) -> bool:
        """Determine if a job should be retried based on attempt count and failure classification."""
        if attempt >= self.max_retries:
            return False
        return self.is_transient_error(exc)

    def calculate_delay(self, attempt: int) -> float:
        """Compute exponential backoff delay with optional jitter: d_n = min(d_max, d_0 * 2^n) + jitter."""
        base_delay = min(
            self.max_delay_seconds,
            self.initial_delay_seconds * (self.backoff_multiplier ** max(0, attempt - 1)),
        )
        if self.jitter:
            jitter_amount = random.uniform(0, 0.5 * base_delay)
            return round(base_delay + jitter_amount, 3)
        return round(base_delay, 3)

    def sleep_before_retry(self, attempt: int) -> float:
        """Helper to sleep for the calculated backoff delay."""
        delay = self.calculate_delay(attempt)
        time.sleep(delay)
        return delay


default_retry_policy = RetryPolicy()
