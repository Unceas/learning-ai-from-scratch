"""Modular tools definitions for assistant function execution."""

from vector_store import hybrid_search
from reranker import rerank


def calculator(a: float, b: float, operation: str):

    if operation == "add":
        return a + b

    if operation == "subtract":
        return a - b

    if operation == "multiply":
        return a * b

    if operation == "divide":
        if b == 0:
            return "Division by zero is not allowed."

        return a / b

    return "Unsupported operation."


def document_search(query: str, filename: str = None, user_id: str = None):

    candidates = hybrid_search(
        query,
        filename=filename,
        user_id=user_id,
        top_k=20
    )

    ranked = rerank(
        query,
        candidates
    )

    results = ranked[:5]

    return [
        {
            "text": result["text"],
            "document": result.get("document", "Unknown"),
            "page": result.get("page"),
            "chunk": result.get("chunk"),
            "user_id": result.get("user_id", user_id)
        }
        for result in results
    ]


TOOLS = {
    "calculator": calculator,
    "document_search": document_search
}
