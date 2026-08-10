"""Persistent semantic long-term memory store using ChromaDB with multi-user isolation."""

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


def add_memory(
    user_id: str,
    text: str,
    importance: float = 0.5,
    memory_type: str = "general",
    metadata: dict = None
) -> None:
    """Store a persistent memory snippet into ChromaDB with user_id isolation."""
    if not text or not text.strip() or not user_id:
        return

    memory_id = f"memory_{collection.count()}"

    embedding = model.encode(
        [text]
    ).tolist()[0]

    meta = {
        "user_id": str(user_id),
        "importance": float(importance),
        "type": str(memory_type)
    }
    if metadata:
        meta.update(metadata)

    collection.add(
        ids=[memory_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[meta]
    )


def search_memory(
    user_id: str,
    query: str,
    top_k: int = 5
) -> list:
    """Perform semantic search over persistent user memories filtered strictly by user_id."""
    if collection.count() == 0 or not query or not query.strip() or not user_id:
        return []

    effective_k = min(top_k, collection.count())

    query_embedding = model.encode(
        [query]
    ).tolist()[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=effective_k,
        where={
            "user_id": str(user_id)
        }
    )

    memories = []
    if result and "documents" in result and result["documents"]:
        docs = result["documents"][0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for i, text in enumerate(docs):
            meta = metadatas[i] if i < len(metadatas) and isinstance(metadatas[i], dict) else {}
            dist = distances[i] if i < len(distances) else 0.0

            memories.append({
                "text": text,
                "importance": float(meta.get("importance", 0.5)),
                "type": meta.get("type", "general"),
                "distance": float(dist),
                "user_id": meta.get("user_id", user_id)
            })

    return memories


def clear_memory(user_id: str = None) -> None:
    """Delete long-term memories for a specific user_id or all memories if un-specified."""
    data = collection.get(where={"user_id": str(user_id)} if user_id else None)
    ids = data.get("ids", [])
    if ids:
        collection.delete(
            ids=ids
        )
