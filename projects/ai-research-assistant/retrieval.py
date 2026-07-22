from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_pages(pages, chunk_size=500):
    chunks = []
    chunk_id = 0
    for p in pages:
        text = p["text"]
        page_num = p["page"]
        for i in range(0, len(text), chunk_size):
            chunks.append({
                "text": text[i:i + chunk_size],
                "page": page_num,
                "chunk": chunk_id
            })
            chunk_id += 1
    return chunks


def chunk_text(text, chunk_size=500):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def retrieve(query, chunks, top_k=3):
    documents = chunks + [query]

    vectorizer = TfidfVectorizer(
        stop_words="english"
    )

    tfidf = vectorizer.fit_transform(
        documents
    )

    query_vector = tfidf[-1]
    chunk_vectors = tfidf[:-1]

    similarities = cosine_similarity(
        query_vector,
        chunk_vectors
    )[0]

    ranked = sorted(
        zip(similarities, chunks),
        reverse=True
    )

    return ranked[:top_k]
