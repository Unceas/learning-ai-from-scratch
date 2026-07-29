"""Gemini LLM integration module for RAG answer generation."""

import os
from typing import Any, Generator, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from prompts import SYSTEM_PROMPT

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key and api_key != "YOUR_API_KEY":
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT
    )
else:
    model = None


def generate_answer(
    query: str,
    results: List[Any],
    memory: Optional[Any] = None
) -> Generator[str, None, None]:
    """Generate a grounded streaming response using Gemini LLM and retrieved context.

    Args:
        query: User question string.
        results: List of retrieved context chunk dictionaries or text strings.
        memory: Optional ConversationMemory instance.

    Yields:
        Generated text chunks progressively.
    """
    if not model:
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
        response = model.generate_content(
            prompt,
            stream=True
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        yield f"⚠️ API Error during answer generation: {str(e)}"
