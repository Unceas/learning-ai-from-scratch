"""Persistent ChromaDB vector database manager for document embedding index and retrieval with multi-user isolation."""

from typing import Any, Dict, List, Optional
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize persistent ChromaDB storage client and collection
client = chromadb.PersistentClient(path="./vector_db")

collection = client.get_or_create_collection(
    name="research_documents"
)

# Initialize SentenceTransformer embedding model
model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def add_document(filename: str, chunks: List[Any], user_id: Optional[str] = None) -> None:
    """Add and index document text chunks and metadata in persistent ChromaDB with user isolation.

    Args:
        filename: Name of the document file.
        chunks: List of chunk strings or structured chunk dictionaries.
        user_id: Optional user identity string.
    """
    if not chunks:
        return

    uid = user_id or "default_user"

    if isinstance(chunks[0], dict):
        texts = [c["text"] for c in chunks]
        metadatas = [
            {
                "user_id": str(uid),
                "document": str(filename),
                "chunk": c.get("chunk", i),
                "page": c.get("page", 1)
            }
            for i, c in enumerate(chunks)
        ]
        ids = [f"{uid}_{filename}_{c.get('chunk', i)}" for i, c in enumerate(chunks)]
    else:
        texts = chunks
        metadatas = [
            {
                "user_id": str(uid),
                "document": str(filename),
                "chunk": i,
                "page": 1
            }
            for i in range(len(chunks))
        ]
        ids = [f"{uid}_{filename}_{i}" for i in range(len(chunks))]

    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )


def build_where_clause(filename: Optional[str] = None, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Construct ChromaDB metadata filtering dictionary combining user_id and filename."""
    conds = []
    if user_id:
        conds.append({"user_id": str(user_id)})
    if filename:
        conds.append({"document": str(filename)})

    if not conds:
        return None
    if len(conds) == 1:
        return conds[0]
    return {"$and": conds}


def search(query: str, filename: Optional[str] = None, user_id: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
    """Perform dense vector embedding search in ChromaDB with user_id metadata filtering.

    Args:
        query: User search query string.
        filename: Optional filename to filter search results by metadata.
        user_id: Optional user identifier filter.
        top_k: Number of top matching context chunks to retrieve.

    Returns:
        List of structured chunk dictionaries.
    """
    total_count = collection.count()
    if total_count == 0 or top_k <= 0 or not query.strip():
        return []

    effective_k = min(top_k, total_count)
    embedding = model.encode([query]).tolist()
    where_clause = build_where_clause(filename=filename, user_id=user_id)

    result = collection.query(
        query_embeddings=embedding,
        n_results=effective_k,
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
            "chunk": meta.get("chunk", 0) if meta else 0,
            "user_id": meta.get("user_id", user_id) if meta else user_id
        })

    return retrieved


def hybrid_search(query: str, filename: Optional[str] = None, user_id: Optional[str] = None, top_k: int = 20) -> List[Dict[str, Any]]:
    """Perform hybrid search combining dense embedding search with TF-IDF keyword search with user isolation.

    Args:
        query: User search query string.
        filename: Optional document metadata filter.
        user_id: Optional user identity filter.
        top_k: Number of top candidate chunks to return.

    Returns:
        List of top ranked chunk dictionaries.
    """
    vector_results = search(query, filename=filename, user_id=user_id, top_k=top_k)

    where_clause = build_where_clause(filename=filename, user_id=user_id)
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
                        "chunk": meta.get("chunk", 0),
                        "user_id": meta.get("user_id", user_id)
                    }
                break

    sorted_cids = sorted(score_map.keys(), key=lambda k: score_map[k], reverse=True)[:top_k]
    return [chunk_map[cid] for cid in sorted_cids]
