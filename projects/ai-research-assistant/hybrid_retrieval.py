from retrieval import retrieve
from embedding_retrieval import retrieve_semantic


def hybrid_search(query, chunks, top_k=3):

    semantic = retrieve_semantic(query, chunks, top_k * 2)
    keyword = retrieve(query, chunks, top_k * 2)

    scores = {}

    for score, chunk in semantic:
        scores[chunk] = scores.get(chunk, 0) + score

    for score, chunk in keyword:
        scores[chunk] = scores.get(chunk, 0) + score

    ranked = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]
