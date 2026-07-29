"""Modular tools definitions for assistant function execution."""

from typing import Any, Dict, List, Optional, Union
import vector_store
from reranker import rerank


def calculator(a: Union[int, float, str], b: Union[int, float, str], operation: str) -> Union[float, str]:
    """Perform basic arithmetic calculations.

    Args:
        a: First operand.
        b: Second operand.
        operation: Calculation operation ('add', 'subtract', 'multiply', 'divide').

    Returns:
        Calculated numerical result or error message string.
    """
    try:
        num_a = float(a)
        num_b = float(b)
    except (ValueError, TypeError):
        return "Invalid numeric input operands."

    op = str(operation).lower().strip()

    if op == "add":
        return num_a + num_b
    if op == "subtract":
        return num_a - num_b
    if op == "multiply":
        return num_a * num_b
    if op == "divide":
        if num_b == 0:
            return "Division by zero is not allowed."
        return num_a / num_b

    return f"Unknown operation '{operation}'."


def document_search(query: str, search_function: Optional[Any] = None, filename: Optional[str] = None, **kwargs) -> List[Dict[str, Any]]:
    """Search uploaded research documents for information relevant to a query.

    Args:
        query: Search query string.
        search_function: Optional custom search callable.
        filename: Optional document filter.

    Returns:
        List of top 5 re-ranked context chunk dictionaries.
    """
    if search_function:
        return search_function(query, filename=filename, **kwargs)

    candidates = vector_store.hybrid_search(query, filename=filename, top_k=20)
    ranked = rerank(query, candidates)
    return ranked[:5]


TOOLS = {
    "calculator": calculator,
    "document_search": document_search
}
