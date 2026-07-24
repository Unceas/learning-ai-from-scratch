from sentence_transformers import CrossEncoder

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)


def rerank(query, retrieved_chunks):

    if not retrieved_chunks:
        return []

    pairs = [
        (query, chunk["text"])
        for chunk in retrieved_chunks
    ]

    scores = reranker.predict(pairs)

    ranked = sorted(
        zip(scores, retrieved_chunks),
        reverse=True,
        key=lambda x: x[0]
    )

    result_chunks = []
    for score, chunk in ranked:
        updated_chunk = dict(chunk)
        updated_chunk["rerank_score"] = float(score)
        result_chunks.append(updated_chunk)

    return result_chunks
