"""Asynchronous RAG pipeline preparation module."""

import asyncio
from typing import Any, Dict, Optional
import vector_store
from reranker import rerank
from llm import generate_answer


async def rag_pipeline(query: str, filename: Optional[str] = None, memory: Optional[Any] = None) -> str:
    """Asynchronously execute retrieval, re-ranking, and answer generation pipeline.

    Args:
        query: User search query string.
        filename: Optional document metadata filter.
        memory: Optional ConversationMemory instance.

    Returns:
        Complete generated answer text.
    """
    retrieved = vector_store.hybrid_search(query, filename=filename, top_k=20)

    ranked = rerank(query, retrieved)

    context_chunks = ranked[:5]

    answer_tokens = []
    for token in generate_answer(query, context_chunks, memory):
        answer_tokens.append(token)

    return "".join(answer_tokens)
