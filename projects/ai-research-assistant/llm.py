"""Gemini LLM integration module for RAG answer generation with multi-user isolation."""

import asyncio
import os
import threading
from typing import Any, AsyncGenerator, Generator, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT
from memory_store import search_memory
from memory_manager import default_memory_manager
from backend.services.rag_context import build_rag_context
from backend.config import settings

load_dotenv()

_llm_concurrency = getattr(settings, "max_llm_concurrency", 8)
llm_semaphore = threading.BoundedSemaphore(max(1, _llm_concurrency))
_async_llm_semaphore = asyncio.Semaphore(max(1, _llm_concurrency))


def get_client(override_api_key: Optional[str] = None) -> Optional[genai.Client]:
    """Retrieve Gemini client using provided or environment API key."""
    api_key = override_api_key
    if not api_key:
        if settings.llm_api_key:
            api_key = settings.llm_api_key.get_secret_value()
        else:
            api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")

    if api_key and api_key not in ("YOUR_API_KEY", "your-local-development-key"):
        return genai.Client(api_key=api_key)
    return None


def generate_answer(
    query: str,
    results: Optional[List[Any]] = None,
    memory: Optional[Any] = None,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    context: Optional[str] = None
) -> Generator[str, None, None]:
    """Generate a grounded streaming response using Gemini LLM and retrieved context.

    Args:
        query: User question string.
        results: Optional list of retrieved context chunk dictionaries or text strings.
        memory: Optional ConversationMemory instance.
        user_id: Optional user identifier string for memory isolation.
        api_key: Optional API key override.
        context: Optional pre-built context string from RAG context builder.

    Yields:
        Generated text chunks progressively.
    """
    # 1. Resolve structured context and check for zero-chunk condition early
    if context is None:
        rag_payload = build_rag_context(results or [])
        if not rag_payload["has_context"]:
            yield rag_payload["fallback_answer"]
            return
        formatted_context = rag_payload["context"]
    else:
        if not context.strip():
            yield "I couldn't find enough information in the indexed documents."
            return
        formatted_context = context

    client = get_client(api_key)
    if not client:
        yield "⚠️ GEMINI_API_KEY is missing or invalid in your .env configuration file."
        return

    conversation = memory.context() if memory and hasattr(memory, "context") else ""

    raw_memories = search_memory(user_id, query, top_k=5) if user_id else []
    filtered_memories = default_memory_manager.filter_memories(raw_memories, minimum_importance=0.4)

    memory_strings = [
        f"- [{m.get('type', 'general').upper()} | Imp: {m.get('importance', 0.5):.1f}] {m.get('text', '')}"
        for m in filtered_memories
        if isinstance(m, dict) and m.get("text")
    ]
    memory_context = "\n".join(memory_strings) if memory_strings else "None"

    prompt = f"""
Relevant Persistent Long-Term Memories

{memory_context}

Previous Conversation

{conversation}

Research Context:

{formatted_context}

User Question:

{query}

Rules:
1. Use the provided context as the primary source.
2. Do not invent unsupported facts.
3. When making a factual claim supported by a source, include its source identifier (e.g. [S1]).
4. Use only source identifiers that actually exist in the provided context.
5. If the context does not contain enough information, say so.
6. Do not create or modify source identifiers.
"""

    try:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        )
        with llm_semaphore:
            response = client.models.generate_content_stream(
                model=getattr(settings, "llm_model", "gemini-2.5-flash"),
                contents=prompt,
                config=config
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text
    except Exception as e:
        yield f"⚠️ API Error during answer generation: {str(e)}"


async def async_generate_answer(
    query: str,
    results: Optional[List[Any]] = None,
    memory: Optional[Any] = None,
    user_id: Optional[str] = None,
    api_key: Optional[str] = None,
    context: Optional[str] = None,
    timeout: Optional[float] = None
) -> str:
    """Asynchronously generate a grounded response using Gemini LLM with bounded concurrency and timeout.

    Returns the full generated answer text.
    """
    exec_timeout = timeout if timeout is not None else getattr(settings, "llm_request_timeout_seconds", 60.0)

    # 1. Resolve structured context
    if context is None:
        rag_payload = build_rag_context(results or [])
        if not rag_payload["has_context"]:
            return rag_payload["fallback_answer"]
        formatted_context = rag_payload["context"]
    else:
        if not context.strip():
            return "I couldn't find enough information in the indexed documents."
        formatted_context = context

    client = get_client(api_key)
    if not client:
        return "⚠️ GEMINI_API_KEY is missing or invalid in your .env configuration file."

    conversation = memory.context() if memory and hasattr(memory, "context") else ""

    raw_memories = search_memory(user_id, query, top_k=5) if user_id else []
    filtered_memories = default_memory_manager.filter_memories(raw_memories, minimum_importance=0.4)

    memory_strings = [
        f"- [{m.get('type', 'general').upper()} | Imp: {m.get('importance', 0.5):.1f}] {m.get('text', '')}"
        for m in filtered_memories
        if isinstance(m, dict) and m.get("text")
    ]
    memory_context = "\n".join(memory_strings) if memory_strings else "None"

    prompt = f"""
Relevant Persistent Long-Term Memories

{memory_context}

Previous Conversation

{conversation}

Research Context:

{formatted_context}

User Question:

{query}

Rules:
1. Use the provided context as the primary source.
2. Do not invent unsupported facts.
3. When making a factual claim supported by a source, include its source identifier (e.g. [S1]).
4. Use only source identifiers that actually exist in the provided context.
5. If the context does not contain enough information, say so.
6. Do not create or modify source identifiers.
"""

    async with _async_llm_semaphore:
        try:
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT
            )

            async def _call_api() -> str:
                effective_model = getattr(settings, "llm_model", "gemini-2.5-flash")
                if hasattr(client, "aio") and hasattr(client.aio, "models"):
                    resp = await client.aio.models.generate_content(
                        model=effective_model,
                        contents=prompt,
                        config=config
                    )
                    return getattr(resp, "text", str(resp))
                else:
                    # Fallback to offloaded sync call
                    def _sync_call():
                        resp = client.models.generate_content(
                            model=effective_model,
                            contents=prompt,
                            config=config
                        )
                        return getattr(resp, "text", str(resp))
                    return await asyncio.to_thread(_sync_call)

            return await asyncio.wait_for(_call_api(), timeout=exec_timeout)
        except asyncio.TimeoutError:
            return f"⚠️ LLM generation timed out after {exec_timeout}s."
        except Exception as e:
            return f"⚠️ API Error during answer generation: {str(e)}"
