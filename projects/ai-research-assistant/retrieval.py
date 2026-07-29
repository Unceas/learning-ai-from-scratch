"""TF-IDF keyword retrieval and text chunking utilities."""

from typing import Any, Dict, List, Tuple, Union
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_pages(pages: List[Dict[str, Any]], chunk_size: int = 500) -> List[Dict[str, Union[int, str]]]:
    """Split page contents into structured chunk dictionaries with page metadata.

    Args:
        pages: List of page dicts with 'page' and 'text' keys.
        chunk_size: Character length of each chunk.

    Returns:
        List of chunk dicts containing 'text', 'page', and 'chunk' ID.
    """
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
    """Split raw text string into a list of fixed-size text chunks.

    Args:
        text: Input string.
        chunk_size: Character length of each chunk.

    Returns:
        List of text chunk strings.
    """
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk_slice = text[i:i + chunk_size]
        if chunk_slice.strip():
            chunks.append(chunk_slice)
    return chunks


def retrieve(query: str, chunks: List[str], top_k: int = 3) -> List[Tuple[float, str]]:
    """Retrieve top-K matching text chunks using TF-IDF vectorization and cosine similarity.

    Args:
        query: User search query string.
        chunks: List of candidate chunk strings.
        top_k: Number of top matching chunks to return.

    Returns:
        List of (similarity_score, chunk_text) tuples sorted by relevance descending.
    """
    if not chunks or top_k <= 0 or not query.strip():
        return []

    documents = chunks + [query]

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform(documents)
    except ValueError:
        # Fallback if text contains no valid vocabulary (e.g. only stop words or numbers)
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
