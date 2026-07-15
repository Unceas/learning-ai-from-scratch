import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(path="./vector_db")

collection = client.get_or_create_collection(
    name="research_documents"
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def add_document(filename, chunks):

    embeddings = model.encode(chunks).tolist()

    collection.add(
        ids=[
            f"{filename}_{i}"
            for i in range(len(chunks))
        ],

        documents=chunks,

        embeddings=embeddings,

        metadatas=[
            {
                "document": filename,
                "chunk": i
            }

            for i in range(len(chunks))
        ]
    )


def search(query, filename=None, top_k=3):

    embedding = model.encode(
        [query]
    ).tolist()

    where_clause = {"document": filename} if filename else None

    result = collection.query(
        query_embeddings=embedding,
        n_results=top_k,
        where=where_clause
    )

    return result
