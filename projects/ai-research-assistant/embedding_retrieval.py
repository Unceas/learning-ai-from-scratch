from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def retrieve_semantic(
    query,
    chunks,
    top_k=3
):

    chunk_embeddings = model.encode(
        chunks
    )

    query_embedding = model.encode(
        [query]
    )

    similarities = cosine_similarity(
        query_embedding,
        chunk_embeddings
    )[0]

    ranked = sorted(
        zip(similarities, chunks),
        reverse=True
    )

    return ranked[:top_k]
