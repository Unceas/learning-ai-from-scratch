"""Document retrieval layer providing secure, document-level filtered semantic retrieval and keyword utilities."""

from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.services.document_db_service import get_indexed_document_ids
from backend.services.embedding_service import EmbeddingService
from backend.services.vector_store import VectorStore


def chunk_pages(pages: List[Dict[str, Any]], chunk_size: int = 500) -> List[Dict[str, Union[int, str]]]:
    """Split page contents into structured chunk dictionaries with page metadata."""
    chunks = []
    chunk_id = 0
    for p in pages:
        text = p.get("text", "")
        page_num = p.get("page", 1)
        for i in range(0, len(text), chunk_size):
            chunk_slice = text[i:i + chunk_size]
            if chunk_slice.strip():
                chunks.append({
                    "text": chunk_slice,
                    "page": page_num,
                    "chunk": chunk_id
                })
                chunk_id += 1
    return chunks


def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    """Split raw text string into a list of fixed-size text chunks."""
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk_slice = text[i:i + chunk_size]
        if chunk_slice.strip():
            chunks.append(chunk_slice)
    return chunks


def tfidf_retrieve(query: str, chunks: List[str], top_k: int = 3) -> List[Tuple[float, str]]:
    """Retrieve top-K matching text chunks using TF-IDF vectorization and cosine similarity."""
    if not chunks or top_k <= 0 or not query.strip():
        return []

    documents = chunks + [query]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform(documents)
    except ValueError:
        return [(0.0, chunk) for chunk in chunks[:top_k]]

    query_vector = tfidf[-1]
    chunk_vectors = tfidf[:-1]

    similarities = cosine_similarity(query_vector, chunk_vectors)[0]

    ranked = sorted(
        zip(similarities, chunks),
        reverse=True,
        key=lambda x: x[0]
    )

    return ranked[:top_k]


def db_retrieve(
    db: Session,
    user_id: str,
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Retrieve top-K relevant chunks strictly scoped to indexed documents belonging to authenticated user.
    
    Returns structured results including document metadata for citation attribution:
    {
        "text": "...",
        "score": 0.82,
        "document_id": 12,
        "filename": "...",
        "chunk_index": 7
    }
    """
    if not query or not query.strip():
        return []

    indexed_document_ids = get_indexed_document_ids(db, user_id)
    if not indexed_document_ids:
        return []

    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed_query(query)

    vector_store = VectorStore()
    results = vector_store.search(
        query_embedding=query_embedding,
        user_id=user_id,
        document_ids=indexed_document_ids,
        top_k=top_k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved = []
    for doc_text, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        # Convert cosine distance to a similarity score (0.0 to 1.0)
        score = round(max(0.0, 1.0 - float(distance)), 4)
        retrieved.append({
            "text": doc_text,
            "score": score,
            "vector_score": score,
            "document_id": metadata.get("document_id"),
            "filename": metadata.get("filename", metadata.get("document", "Unknown")),
            "chunk_index": metadata.get("chunk_index", metadata.get("chunk_id", 0)),
            "page": metadata.get("page", 1),
            "file_hash": metadata.get("file_hash")
        })

    return retrieved


def db_keyword_retrieve(
    db: Session,
    user_id: str,
    query: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Retrieve top-K matching chunks using BM25 keyword search strictly scoped to user's indexed docs."""
    if not query or not query.strip():
        return []

    indexed_document_ids = get_indexed_document_ids(db, user_id)
    if not indexed_document_ids:
        return []

    vector_store = VectorStore()
    user_chunks = vector_store.get_user_chunks(user_id=user_id, document_ids=indexed_document_ids)
    if not user_chunks:
        return []

    from backend.services.keyword_retriever import KeywordRetriever
    retriever = KeywordRetriever(user_chunks)
    kw_results = retriever.retrieve(query=query, top_k=top_k)

    retrieved = []
    for item in kw_results:
        chunk = item["chunk"]
        retrieved.append({
            "text": chunk.get("text", ""),
            "score": item["score"],
            "keyword_score": item["score"],
            "document_id": chunk.get("document_id"),
            "filename": chunk.get("filename", "Unknown"),
            "chunk_index": chunk.get("chunk_index", 0),
            "page": chunk.get("page", 1),
            "file_hash": chunk.get("file_hash")
        })
    return retrieved


def db_hybrid_retrieve(
    db: Session,
    user_id: str,
    query: str,
    dense_k: int = 10,
    keyword_k: int = 10,
    top_k: int = 10,
    rrf_k: int = 60
) -> List[Dict[str, Any]]:
    """Retrieve candidate chunks using hybrid dense + BM25 keyword search fused with Reciprocal Rank Fusion."""
    dense_res = db_retrieve(db=db, user_id=user_id, query=query, top_k=dense_k)
    kw_res = db_keyword_retrieve(db=db, user_id=user_id, query=query, top_k=keyword_k)

    from backend.services.rank_fusion import reciprocal_rank_fusion
    fused = reciprocal_rank_fusion([dense_res, kw_res], k=rrf_k)

    return [item["chunk"] for item in fused[:top_k]]


def retrieve(*args, **kwargs):
    """Adaptive retrieve interface routing to either db_retrieve or tfidf_retrieve based on arguments."""
    if args and isinstance(args[0], str):
        return tfidf_retrieve(*args, **kwargs)
    if "chunks" in kwargs:
        return tfidf_retrieve(*args, **kwargs)
    return db_retrieve(*args, **kwargs)
