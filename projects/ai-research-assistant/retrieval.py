import re


def chunk_text(text, chunk_size=500):

    chunks = []

    for i in range(0, len(text), chunk_size):

        chunks.append(
            text[i:i + chunk_size]
        )

    return chunks


def score_chunk(query, chunk):

    query_words = set(
        re.findall(r"\w+", query.lower())
    )

    chunk_words = set(
        re.findall(r"\w+", chunk.lower())
    )

    return len(
        query_words.intersection(chunk_words)
    )


def retrieve(query, chunks):

    scored = []

    for chunk in chunks:

        score = score_chunk(
            query,
            chunk
        )

        scored.append(
            (score, chunk)
        )

    scored.sort(
        reverse=True,
        key=lambda x: x[0]
    )

    return scored[:3]
