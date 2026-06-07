import re
from collections import Counter


def chunk_text(text, chunk_size=500):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)

    return chunks


def _tokenize(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_relevant_chunks(query, chunks, top_k=3):
    query_tokens = Counter(_tokenize(query))
    scored_chunks = []

    for chunk in chunks:
        chunk_tokens = Counter(_tokenize(chunk))
        score = sum(query_tokens[token] * chunk_tokens[token] for token in query_tokens)
        if score > 0:
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored_chunks[:top_k]]
