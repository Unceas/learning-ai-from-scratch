import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.embedding_cache import EmbeddingCache


def test_repeated_text_uses_cached_embedding():
    cache = EmbeddingCache(max_entries=10)
    calls = []

    def compute(text):
        calls.append(text)
        return [1.0, 2.0, 3.0]

    first = cache.get_or_compute(
        "attention",
        compute,
        model_version="v1",
    )
    second = cache.get_or_compute(
        "attention",
        compute,
        model_version="v1",
    )

    assert first == second
    assert len(calls) == 1
    assert cache.stats()["hits"] == 1


def test_model_version_separates_entries():
    cache = EmbeddingCache()

    def compute(text):
        return [float(len(text))]

    cache.get_or_compute(
        "attention",
        compute,
        model_version="v1",
    )
    cache.get_or_compute(
        "attention",
        compute,
        model_version="v2",
    )

    assert cache.stats()["misses"] == 2


def test_cache_evicts_oldest_entry():
    cache = EmbeddingCache(max_entries=2)

    def compute(text):
        return [float(len(text))]

    for text in ["a", "b", "c"]:
        cache.get_or_compute(
            text,
            compute,
            model_version="v1",
        )

    assert cache.stats()["entries"] == 2
    assert cache.stats()["evictions"] == 1


def test_cached_vectors_are_not_mutable_by_callers():
    cache = EmbeddingCache()

    def compute(text):
        return [1.0, 2.0]

    vector = cache.get_or_compute(
        "attention",
        compute,
        model_version="v1",
    )
    vector[0] = 999.0

    again = cache.get_or_compute(
        "attention",
        compute,
        model_version="v1",
    )

    assert again == [1.0, 2.0]


def test_different_namespaces_separate_entries():
    cache = EmbeddingCache()
    calls = []

    def compute(text):
        calls.append(text)
        return [4.0, 5.0]

    vec_alice = cache.get_or_compute(
        "transformer",
        compute,
        model_version="v1",
        namespace="user:alice",
    )
    vec_bob = cache.get_or_compute(
        "transformer",
        compute,
        model_version="v1",
        namespace="user:bob",
    )

    assert vec_alice == vec_bob
    assert len(calls) == 2
    assert cache.stats()["misses"] == 2
    assert cache.stats()["hits"] == 0


def test_clearing_cache_forces_recomputation():
    cache = EmbeddingCache()
    calls = []

    def compute(text):
        calls.append(text)
        return [1.0]

    cache.get_or_compute("attention", compute, model_version="v1")
    assert len(calls) == 1

    cache.clear()
    assert cache.stats()["entries"] == 0

    cache.get_or_compute("attention", compute, model_version="v1")
    assert len(calls) == 2


def test_get_or_compute_batch():
    cache = EmbeddingCache(max_entries=10)
    batch_calls = []

    def compute_batch(missing):
        batch_calls.append(list(missing))
        return [[float(len(t))] for t in missing]

    # Pre-populate one entry
    cache.get_or_compute("cat", lambda t: [float(len(t))], model_version="v1")

    # Batch lookup: "cat" is cached, "elephant" and "dog" are missing
    results = cache.get_or_compute_batch(
        ["cat", "elephant", "dog"],
        compute_batch,
        model_version="v1",
    )

    assert results == [[3.0], [8.0], [3.0]]
    assert batch_calls == [["elephant", "dog"]]
    assert cache.stats()["hits"] == 1
    assert cache.stats()["misses"] == 3
    assert cache.stats()["entries"] == 3


def test_concurrent_access_is_thread_safe():
    cache = EmbeddingCache(max_entries=50)

    def compute(text):
        return [float(len(text))]

    def worker(worker_id):
        for i in range(20):
            text = f"query_{i % 5}"
            cache.get_or_compute(text, compute, model_version="v1", namespace=f"user:{worker_id % 2}")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stats = cache.stats()
    assert stats["entries"] <= 50
    assert stats["hits"] + stats["misses"] == 8 * 20
