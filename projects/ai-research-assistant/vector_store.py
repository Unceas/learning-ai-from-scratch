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


def hybrid_search(query, filename=None, top_k=20):
    vector_results = search(query, filename=filename, top_k=top_k)

    where_clause = {"document": filename} if filename else None
    all_data = collection.get(where=where_clause)
    all_docs = all_data.get("documents") or []
    all_metas = all_data.get("metadatas") or []

    if not all_docs:
        return vector_results

    from retrieval import retrieve as tfidf_retrieve
    tfidf_res = tfidf_retrieve(query, all_docs, top_k=min(top_k, len(all_docs)))

    score_map = {}
    chunk_map = {}

    for rank, item in enumerate(vector_results):
        cid = (item["document"], item["chunk"])
        score_map[cid] = score_map.get(cid, 0.0) + (1.0 / (rank + 1.0))
        chunk_map[cid] = item

    for rank, (sim, text_match) in enumerate(tfidf_res):
        for doc, meta in zip(all_docs, all_metas):
            if doc == text_match:
                cid = (meta.get("document", "Unknown"), meta.get("chunk", 0))
                score_map[cid] = score_map.get(cid, 0.0) + (1.0 / (rank + 1.0))
                if cid not in chunk_map:
                    chunk_map[cid] = {
                        "text": doc,
                        "document": meta.get("document", "Unknown"),
                        "page": meta.get("page", 1),
                        "chunk": meta.get("chunk", 0)
                    }
                break

    sorted_cids = sorted(score_map.keys(), key=lambda k: score_map[k], reverse=True)[:top_k]
    return [chunk_map[cid] for cid in sorted_cids]
