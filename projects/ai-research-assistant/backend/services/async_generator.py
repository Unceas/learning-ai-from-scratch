"""Asynchronous LLM generation service with bounded concurrency and request timeouts."""

import asyncio
import logging
from typing import Any, AsyncGenerator as AsyncGenType, Callable, Dict, Optional, Union

from backend.config import settings

logger = logging.getLogger(__name__)


class AsyncGenerator:
    """Bounded asynchronous LLM generator enforcing concurrency limits and network timeouts.

    Features:
    - Semaphore-governed concurrency bounding (default: settings.max_concurrent_llm_requests)
    - Enforced operation timeouts via asyncio.wait_for (default: settings.llm_request_timeout_seconds)
    - Fallback and error handling for provider outages and timeout events
    - Operational telemetry (active requests, total requests, timeouts, errors)
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        max_concurrency: Optional[int] = None,
        timeout: Optional[float] = None,
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
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

        # Operational metrics
        self.total_requests = 0
        self.active_requests = 0
        self.completed_requests = 0
        self.timeouts = 0
        self.errors = 0

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._semaphore

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: str = "gemini-2.5-flash",
    ) -> str:
        """Execute an asynchronous generation request bounded by the concurrency semaphore."""
        self.total_requests += 1

        async with self._semaphore:
            self.active_requests += 1
            try:
                result = await asyncio.wait_for(
                    self._call_client(prompt, system_instruction=system_instruction, model=model),
                    timeout=self.timeout,
                )
                self.completed_requests += 1
                return result
            except asyncio.TimeoutError:
                self.timeouts += 1
                logger.error(
                    "Async LLM generation timed out after %.1f seconds",
                    self.timeout,
                )
                raise
            except Exception as exc:
                self.errors += 1
                logger.error("Async LLM generation failed: %s", exc)
                raise
            finally:
                self.active_requests -= 1

    async def _call_client(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
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

    def stats(self) -> Dict[str, Any]:
        """Return operational telemetry for async generator."""
        return {
            "max_concurrency": self.max_concurrency,
            "timeout_seconds": self.timeout,
            "active_requests": self.active_requests,
            "total_requests": self.total_requests,
            "completed_requests": self.completed_requests,
            "timeouts": self.timeouts,
            "errors": self.errors,
        }

    def reset_stats(self) -> None:
        """Reset operational telemetry counters."""
        self.total_requests = 0
        self.active_requests = 0
        self.completed_requests = 0
        self.timeouts = 0
        self.errors = 0


default_async_generator = AsyncGenerator()
