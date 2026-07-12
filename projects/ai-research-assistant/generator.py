def generate_answer(query, retrieved_chunks):

    if not retrieved_chunks:
        return "No relevant information found."

    context = "\n\n".join(
        retrieved_chunks
    )

    answer = (
        "Based on the retrieved document sections:\n\n"
        + context[:1500]
    )

    return answer
