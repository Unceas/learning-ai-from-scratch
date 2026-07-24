import json
import time
import os
import vector_store
from retrieval import retrieve as tfidf_retrieve
from reranker import rerank


def recall_at_k(expected, retrieved):
    return int(expected in retrieved)


def precision_at_k(expected, retrieved):
    if not retrieved:
        return 0.0
    return retrieved.count(expected) / len(retrieved)


def load_evaluation_dataset(filepath="evaluation.json"):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def evaluate_retrieval(dataset=None, filename=None):
    if dataset is None:
        dataset = load_evaluation_dataset()

    if not dataset:
        return {
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "precision_at_3": 0.0,
            "mean_recall": 0.0,
            "avg_latency_ms": 0.0,
            "total_queries": 0,
            "num_indexed_docs": 0
        }

    existing = vector_store.collection.get()
    existing_metadatas = existing.get("metadatas") or []
    num_indexed_docs = len(set(
        meta["document"] for meta in existing_metadatas if meta and "document" in meta
    ))

    r1_scores = []
    r3_scores = []
    r5_scores = []
    p3_scores = []
    latencies = []

    for sample in dataset:
        query = sample["query"]
        expected = sample["expected_chunk"]

        start_time = time.time()
        candidates = vector_store.hybrid_search(query, filename=filename, top_k=20)
        retrieved_results = rerank(query, candidates)[:5]
        elapsed_ms = (time.time() - start_time) * 1000.0

        retrieved_chunk_ids = [c["chunk"] for c in retrieved_results]

        r1_scores.append(recall_at_k(expected, retrieved_chunk_ids[:1]))
        r3_scores.append(recall_at_k(expected, retrieved_chunk_ids[:3]))
        r5_scores.append(recall_at_k(expected, retrieved_chunk_ids[:5]))
        p3_scores.append(precision_at_k(expected, retrieved_chunk_ids[:3]))
        latencies.append(elapsed_ms)

    total = len(dataset)
    mean_r1 = sum(r1_scores) / total
    mean_r3 = sum(r3_scores) / total
    mean_r5 = sum(r5_scores) / total
    mean_p3 = sum(p3_scores) / total
    avg_latency = sum(latencies) / total

    return {
        "recall_at_1": mean_r1,
        "recall_at_3": mean_r3,
        "recall_at_5": mean_r5,
        "precision_at_3": mean_p3,
        "mean_recall": mean_r5,
        "avg_latency_ms": avg_latency,
        "total_queries": total,
        "num_indexed_docs": num_indexed_docs
    }


def compare_retrievers(dataset=None):
    if dataset is None:
        dataset = load_evaluation_dataset()

    if not dataset:
        return []

    all_data = vector_store.collection.get()
    all_docs = all_data.get("documents") or []
    all_metas = all_data.get("metadatas") or []

    if not all_docs:
        return [
            {"Retriever": "TF-IDF", "Recall@5": 0.0, "Latency (ms)": 0.0},
            {"Retriever": "Embeddings", "Recall@5": 0.0, "Latency (ms)": 0.0},
            {"Retriever": "Hybrid", "Recall@5": 0.0, "Latency (ms)": 0.0},
            {"Retriever": "Hybrid + Re-ranker", "Recall@5": 0.0, "Latency (ms)": 0.0}
        ]

    chunk_objects = [
        {"text": doc, "chunk": meta.get("chunk", i), "document": meta.get("document", "doc")}
        for i, (doc, meta) in enumerate(zip(all_docs, all_metas))
    ]

    tfidf_r5 = []
    embed_r5 = []
    hybrid_r5 = []
    rerank_r5 = []

    tfidf_times = []
    embed_times = []
    hybrid_times = []
    rerank_times = []

    text_list = [c["text"] for c in chunk_objects]

    for sample in dataset:
        query = sample["query"]
        expected = sample["expected_chunk"]

        # 1. TF-IDF
        t0 = time.time()
        tfidf_res = tfidf_retrieve(query, text_list, top_k=5)
        tfidf_times.append((time.time() - t0) * 1000.0)

        tfidf_chunk_ids = []
        for _, text_match in tfidf_res:
            for c in chunk_objects:
                if c["text"] == text_match:
                    tfidf_chunk_ids.append(c["chunk"])
                    break
        tfidf_r5.append(recall_at_k(expected, tfidf_chunk_ids))

        # 2. Embeddings
        t0 = time.time()
        embed_res = vector_store.search(query, top_k=5)
        embed_times.append((time.time() - t0) * 1000.0)
        embed_chunk_ids = [c["chunk"] for c in embed_res]
        embed_r5.append(recall_at_k(expected, embed_chunk_ids))

        # 3. Hybrid
        t0 = time.time()
        hybrid_res = vector_store.hybrid_search(query, top_k=5)
        hybrid_times.append((time.time() - t0) * 1000.0)
        hybrid_chunk_ids = [c["chunk"] for c in hybrid_res]
        hybrid_r5.append(recall_at_k(expected, hybrid_chunk_ids))

        # 4. Hybrid + Re-ranker
        t0 = time.time()
        hybrid_candidates = vector_store.hybrid_search(query, top_k=20)
        rerank_res = rerank(query, hybrid_candidates)[:5]
        rerank_times.append((time.time() - t0) * 1000.0)
        rerank_chunk_ids = [c["chunk"] for c in rerank_res]
        rerank_r5.append(recall_at_k(expected, rerank_chunk_ids))

    total = len(dataset)
    return [
        {
            "Retriever": "TF-IDF",
            "Recall@5": sum(tfidf_r5) / total,
            "Latency (ms)": sum(tfidf_times) / total
        },
        {
            "Retriever": "Embeddings",
            "Recall@5": sum(embed_r5) / total,
            "Latency (ms)": sum(embed_times) / total
        },
        {
            "Retriever": "Hybrid",
            "Recall@5": sum(hybrid_r5) / total,
            "Latency (ms)": sum(hybrid_times) / total
        },
        {
            "Retriever": "Hybrid + Re-ranker",
            "Recall@5": sum(rerank_r5) / total,
            "Latency (ms)": sum(rerank_times) / total
        }
    ]
