"""Gemini LLM integration module for RAG answer generation with multi-user isolation."""

import os
from typing import Any, Generator, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT
from memory_store import search_memory
from memory_manager import default_memory_manager
from backend.services.rag_context import build_rag_context

load_dotenv()


def get_client(override_api_key: Optional[str] = None) -> Optional[genai.Client]:
    """Retrieve Gemini client using provided or environment API key."""
    api_key = override_api_key or os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "YOUR_API_KEY":
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
        response = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"⚠️ API Error during answer generation: {str(e)}"
