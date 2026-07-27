import asyncio
import vector_store
from reranker import rerank
from llm import generate_answer


async def rag_pipeline(query, filename=None, memory=None):

    retrieved = vector_store.hybrid_search(query, filename=filename, top_k=20)

    ranked = rerank(query, retrieved)

    context_chunks = ranked[:5]

    answer_tokens = []
    for token in generate_answer(query, context_chunks, memory):
        answer_tokens.append(token)

    return "".join(answer_tokens)
