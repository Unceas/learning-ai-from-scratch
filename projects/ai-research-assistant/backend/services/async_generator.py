"""Asynchronous LLM generation service with bounded concurrency and request timeouts."""

import asyncio
import logging
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


class AsyncGenerator:
    """Bounded asynchronous LLM generator enforcing concurrency limits, timeouts, and bounded retries.

    Features:
    - Semaphore-governed concurrency bounding (default: settings.max_concurrent_llm_requests)
    - Enforced operation timeouts via asyncio.wait_for (default: settings.llm_request_timeout_seconds)
    - Bounded exponential-backoff retries for transient errors and timeouts
    - Fallback and error handling for provider outages and timeout events
    - Operational telemetry (active requests, total requests, timeouts, errors, retries)
    """

    def __init__(
        self,
        client: Any | None = None,
        max_concurrency: int | None = None,
        timeout: float | None = None,
        max_retries: int = 2,
        backoff_factor: float = 0.05,
    ):
        concurrency = (
            max_concurrency
            if max_concurrency is not None
            else getattr(settings, "max_concurrent_llm_requests", 8)
        )
        if concurrency < 1:
            raise ValueError("max_concurrency must be at least 1")

        self.client = client
        self.max_concurrency = concurrency
        self.timeout = (
            timeout
            if timeout is not None
            else getattr(settings, "llm_request_timeout_seconds", 60.0)
        )
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

        # Operational metrics
        self.total_requests = 0
        self.active_requests = 0
        self.completed_requests = 0
        self.timeouts = 0
        self.errors = 0
        self.retries = 0

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    async def _send(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str = "gemini-2.5-flash",
    ) -> str:
        """Low-level dispatch point to the external LLM client.

        Seam for deterministic testing of provider timeouts and transient network errors.
        """
        return await self._call_client(prompt, system_instruction=system_instruction, model=model)

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str = "gemini-2.5-flash",
    ) -> str:
        """Execute an asynchronous generation request bounded by concurrency and retries."""
        self.total_requests += 1

        async with self._semaphore:
            self.active_requests += 1
            attempt = 0
            max_attempts = 1 + max(0, self.max_retries)

            try:
                while attempt < max_attempts:
                    attempt += 1
                    try:
                        result = await asyncio.wait_for(
                            self._send(prompt, system_instruction=system_instruction, model=model),
                            timeout=self.timeout,
                        )
                        self.completed_requests += 1
                        return result
                    except (TimeoutError, asyncio.TimeoutError) as exc:
                        if attempt < max_attempts:
                            self.retries += 1
                            logger.warning(
                                "Async LLM attempt %d/%d timed out, retrying...",
                                attempt,
                                max_attempts,
                            )
                            await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                            continue
                        self.timeouts += 1
                        logger.error(
                            "Async LLM generation timed out after %d attempts (timeout=%.1fs)",
                            max_attempts,
                            self.timeout,
                        )
                        raise asyncio.TimeoutError(f"Provider timed out after {max_attempts} attempts") from exc
                    except Exception as exc:
                        # Distinguish retryable transient errors (429, 503, connection errors) from permanent
                        err_msg = str(exc).lower()
                        is_retryable = (
                            "429" in err_msg
                            or "resource exhausted" in err_msg
                            or "503" in err_msg
                            or "service unavailable" in err_msg
                            or "connection" in err_msg
                            or "simulated timeout" in err_msg
                        )
                        if is_retryable and attempt < max_attempts:
                            self.retries += 1
                            logger.warning(
                                "Async LLM attempt %d/%d transient error (%s), retrying...",
                                attempt,
                                max_attempts,
                                exc,
                            )
                            await asyncio.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                            continue

                        self.errors += 1
                        logger.error("Async LLM generation failed on attempt %d/%d: %s", attempt, max_attempts, exc)
                        raise
            finally:
                self.active_requests -= 1

    async def _call_client(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str = "gemini-2.5-flash",
    ) -> str:
        """Internal dispatch to LLM client."""
        if self.client is None:
            # Fallback mock/offline generation response
            await asyncio.sleep(0.01)
            return f"Answer based on context for: {prompt[:30]}..."

        # If client is an awaitable callable
        if callable(self.client):
            res = self.client(prompt)
            if asyncio.iscoroutine(res):
                return await res
            return str(res)

        # If client has aio.models.generate_content (Google GenAI Client)
        if hasattr(self.client, "aio") and hasattr(self.client.aio, "models"):
            config = None
            if system_instruction:
                try:
                    from google.genai import types
                    config = types.GenerateContentConfig(system_instruction=system_instruction)
                except ImportError:
                    pass

            response = await self.client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            return getattr(response, "text", str(response))

        # If client has awaitable generate method
        if hasattr(self.client, "generate"):
            res = self.client.generate(prompt)
            if asyncio.iscoroutine(res):
                response = await res
                return getattr(response, "text", str(response))
            return getattr(res, "text", str(res))

        raise TypeError(f"Unsupported LLM client type: {type(self.client)}")

    def stats(self) -> dict[str, Any]:
        """Return operational telemetry for async generator."""
        return {
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "completed_requests": self.completed_requests,
            "timeouts": self.timeouts,
            "errors": self.errors,
            "retries": self.retries,
        }

    def reset_stats(self) -> None:
        """Reset operational telemetry counters."""
        self.total_requests = 0
        self.active_requests = 0
        self.completed_requests = 0
        self.timeouts = 0
        self.errors = 0
        self.retries = 0


default_async_generator = AsyncGenerator()
