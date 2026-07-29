"""Retrieval evaluation framework for benchmarking Recall@K, Precision@K, and Latency."""

import json
import os
import time
from typing import Any, Dict, List, Optional
import vector_store
from retrieval import retrieve as tfidf_retrieve
from reranker import rerank


def recall_at_k(expected: int, retrieved: List[int]) -> int:
    """Calculate Recall@K binary hit indicator.

    Args:
        expected: Target chunk ID expected.
        retrieved: List of retrieved chunk IDs.

    Returns:
        1 if expected chunk ID is in retrieved list, else 0.
    """
    return int(expected in retrieved)


def precision_at_k(expected: int, retrieved: List[int]) -> float:
    """Calculate Precision@K proportion for target chunk ID.

    Args:
        expected: Target chunk ID expected.
        retrieved: List of retrieved chunk IDs.

    Returns:
        Precision score between 0.0 and 1.0.
    """
    if not retrieved:
        return 0.0
    return retrieved.count(expected) / float(len(retrieved))


def load_evaluation_dataset(filepath: str = "evaluation.json") -> List[Dict[str, Any]]:
    """Load benchmark dataset from JSON file.

    Args:
        filepath: Path to evaluation dataset JSON file.

    Returns:
        List of sample dictionaries containing 'query' and 'expected_chunk'.
    """
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def evaluate_retrieval(dataset: Optional[List[Dict[str, Any]]] = None, filename: Optional[str] = None) -> Dict[str, Any]:
    """Evaluate retrieval pipeline performance against benchmark dataset.

    Args:
        dataset: List of benchmark query dicts.
        filename: Optional document filter.

    Returns:
        Dictionary containing Recall@1, Recall@3, Recall@5, Precision@3, Latency, and Indexed Documents count.
    """
    if dataset is None:
        dataset = load_evaluation_dataset()

    existing = vector_store.collection.get()
    existing_metadatas = existing.get("metadatas") or []
    num_indexed_docs = len(set(
        meta["document"] for meta in existing_metadatas if meta and "document" in meta
    ))

    if not dataset:
        return {
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "precision_at_3": 0.0,
            "mean_recall": 0.0,
            "avg_latency_ms": 0.0,
            "total_queries": 0,
            "num_indexed_docs": num_indexed_docs
        }

    r1_scores = []
    r3_scores = []
    r5_scores = []
    p3_scores = []
    latencies = []

    for sample in dataset:
        query = sample["query"]
        expected = sample["expected_chunk"]

        start_time = time.perf_counter()
        candidates = vector_store.hybrid_search(query, filename=filename, top_k=20)
        retrieved_results = rerank(query, candidates)[:5]
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

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


def compare_retrievers(dataset: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """Compare Recall@5 and Latency across TF-IDF, Embeddings, Hybrid, and Hybrid + Re-ranker strategies.

    Args:
        dataset: List of benchmark query dicts.

    Returns:
        List of result dictionaries for each retrieval method.
    """
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
        t0 = time.perf_counter()
        tfidf_res = tfidf_retrieve(query, text_list, top_k=5)
        tfidf_times.append((time.perf_counter() - t0) * 1000.0)

        tfidf_chunk_ids = []
        for _, text_match in tfidf_res:
            for c in chunk_objects:
                if c["text"] == text_match:
                    tfidf_chunk_ids.append(c["chunk"])
                    break
        tfidf_r5.append(recall_at_k(expected, tfidf_chunk_ids))

        # 2. Embeddings
        t0 = time.perf_counter()
        embed_res = vector_store.search(query, top_k=5)
        embed_times.append((time.perf_counter() - t0) * 1000.0)
        embed_chunk_ids = [c["chunk"] for c in embed_res]
        embed_r5.append(recall_at_k(expected, embed_chunk_ids))

        # 3. Hybrid
        t0 = time.perf_counter()
        hybrid_res = vector_store.hybrid_search(query, top_k=5)
        hybrid_times.append((time.perf_counter() - t0) * 1000.0)
        hybrid_chunk_ids = [c["chunk"] for c in hybrid_res]
        hybrid_r5.append(recall_at_k(expected, hybrid_chunk_ids))

        # 4. Hybrid + Re-ranker
        t0 = time.perf_counter()
        hybrid_candidates = vector_store.hybrid_search(query, top_k=20)
        rerank_res = rerank(query, hybrid_candidates)[:5]
        rerank_times.append((time.perf_counter() - t0) * 1000.0)
        rerank_chunk_ids = [c["chunk"] for c in rerank_res]
        rerank_r5.append(recall_at_k(expected, rerank_chunk_ids))

    total = float(len(dataset))
    return [
        {
            "Retriever": "TF-IDF",
            "Recall@5": round(sum(tfidf_r5) / total, 2),
            "Latency (ms)": round(sum(tfidf_times) / total, 1)
        },
        {
            "Retriever": "Embeddings",
            "Recall@5": round(sum(embed_r5) / total, 2),
            "Latency (ms)": round(sum(embed_times) / total, 1)
        },
        {
            "Retriever": "Hybrid",
            "Recall@5": round(sum(hybrid_r5) / total, 2),
            "Latency (ms)": round(sum(hybrid_times) / total, 1)
        },
        {
            "Retriever": "Hybrid + Re-ranker",
            "Recall@5": round(sum(rerank_r5) / total, 2),
            "Latency (ms)": round(sum(rerank_times) / total, 1)
        }
    ]
