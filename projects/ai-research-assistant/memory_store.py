"""Persistent semantic long-term memory store using ChromaDB."""

import os
import chromadb
from sentence_transformers import SentenceTransformer

client = chromadb.PersistentClient(
    path="./memory_db"
)

collection = client.get_or_create_collection(
    name="user_memory"
)

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)


def add_memory(text: str, metadata: dict = None) -> None:
    """Store a persistent memory snippet into ChromaDB."""
    if not text or not text.strip():
        return

    memory_id = f"memory_{collection.count()}"

    embedding = model.encode(
        [text]
    ).tolist()[0]

    meta = dict(metadata) if metadata else {"type": "user_memory"}

    collection.add(
        ids=[memory_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[meta]
    )


def search_memory(query: str, top_k: int = 3) -> list:
    """Perform semantic search over persistent user memories."""
    if collection.count() == 0 or not query or not query.strip():
        return []

    effective_k = min(top_k, collection.count())

    query_embedding = model.encode(
        [query]
    ).tolist()[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_k
    )

    if result and "documents" in result and result["documents"]:
        return result["documents"][0]
    return []


def clear_memory() -> None:
    """Delete all stored long-term memories."""
    data = collection.get()
    ids = data.get("ids", [])
    if ids:
        collection.delete(
            ids=ids
        )
