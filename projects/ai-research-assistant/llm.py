"""Gemini LLM integration module for RAG answer generation."""

import os
from typing import Any, Generator, List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from prompts import SYSTEM_PROMPT

load_dotenv()


def get_client(override_api_key: Optional[str] = None) -> Optional[genai.Client]:
    """Retrieve Gemini client using provided or environment API key."""
    api_key = override_api_key or os.getenv("GEMINI_API_KEY")
    if api_key and api_key != "YOUR_API_KEY":
        return genai.Client(api_key=api_key)
    return None


def generate_answer(
    query: str,
    results: List[Any],
    memory: Optional[Any] = None,
    api_key: Optional[str] = None
) -> Generator[str, None, None]:
    """Generate a grounded streaming response using Gemini LLM and retrieved context.

    Args:
        query: User question string.
        results: List of retrieved context chunk dictionaries or text strings.
        memory: Optional ConversationMemory instance.
        api_key: Optional API key override.

    Yields:
        Generated text chunks progressively.
    """
    client = get_client(api_key)
    if not client:
        yield "⚠️ GEMINI_API_KEY is missing or invalid in your .env configuration file."
        return

    conversation = memory.context() if memory and hasattr(memory, "context") else ""

    context = ""
    for i, chunk in enumerate(results, 1):
        text = chunk["text"] if isinstance(chunk, dict) else chunk
        doc = chunk.get("document", "Unknown") if isinstance(chunk, dict) else "Unknown"
        page = chunk.get("page", 1) if isinstance(chunk, dict) else 1
        context += f"""
[Source {i}]

Document:
{doc}

Page:
{page}

Content:
{text}

"""

    prompt = f"""
Previous Conversation

{conversation}

Retrieved Context

{context}

Current Question

{query}

Rules

- Use retrieved context as the primary source.
- Whenever possible, reference the appropriate source number (e.g. [Source 1]).
- Never cite a source that was not provided.
- Use previous conversation only to resolve references.
- Never invent facts.
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

