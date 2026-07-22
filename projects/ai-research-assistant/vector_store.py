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

    if chunks and isinstance(chunks[0], dict):
        texts = [c["text"] for c in chunks]
        metadatas = [
            {
                "document": filename,
                "chunk": c["chunk"],
                "page": c.get("page", 1)
            }
            for c in chunks
        ]
        ids = [f"{filename}_{c['chunk']}" for c in chunks]
    else:
        texts = chunks
        metadatas = [
            {
                "document": filename,
                "chunk": i,
                "page": 1
            }
            for i in range(len(chunks))
        ]
        ids = [f"{filename}_{i}" for i in range(len(chunks))]

    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
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

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    retrieved = []
    for doc, meta in zip(documents, metadatas):
        retrieved.append({
            "text": doc,
            "document": meta.get("document", "Unknown") if meta else "Unknown",
            "page": meta.get("page", 1) if meta else 1,
            "chunk": meta.get("chunk", 0) if meta else 0
        })

    return retrieved
