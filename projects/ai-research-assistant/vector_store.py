import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.Client()

collection = client.get_or_create_collection(
    "documents"
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def index_chunks(chunks):
    global collection

    client.delete_collection(
        "documents"
    )

    collection = client.get_or_create_collection(
        "documents"
    )

    embeddings = model.encode(chunks).tolist()

    ids = [str(i) for i in range(len(chunks))]

    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings
    )


def search(query, k=3):

    query_embedding = model.encode(
        [query]
    ).tolist()

    result = collection.query(
        query_embeddings=query_embedding,
        n_results=k
    )

    return result["documents"][0]
