import vector_store
from reranker import rerank


def calculator(a, b, operation):
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

    return "Unknown operation."


def document_search(query, search_function=None, filename=None, **kwargs):
    if search_function:
        return search_function(query, filename=filename, **kwargs)

    candidates = vector_store.hybrid_search(query, filename=filename, top_k=20)
    ranked = rerank(query, candidates)
    return ranked[:5]


TOOLS = {
    "calculator": calculator,
    "document_search": document_search
}
