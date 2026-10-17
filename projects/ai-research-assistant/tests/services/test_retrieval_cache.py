import os
import sys
import threading
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.retrieval_cache import RetrievalCache


def test_cache_initialization_and_validation():
    cache = RetrievalCache(max_entries=50)
    assert cache.max_entries == 50
    assert cache.stats()["entries"] == 0

    with pytest.raises(ValueError):
        RetrievalCache(max_entries=0)

    with pytest.raises(ValueError):
        RetrievalCache(max_entries=-5)


def test_deterministic_key_generation():
    docs_a = [{"id": 1, "index_version": 1}, {"id": 2, "index_version": 0}]
    docs_a_reversed = [{"id": 2, "index_version": 0}, {"id": 1, "index_version": 1}]
    docs_b = [{"id": 1, "index_version": 2}, {"id": 2, "index_version": 0}]  # doc 1 reindexed
    docs_c = [{"id": 1, "index_version": 1}]  # doc 2 deleted

    config_1 = {"strategy": "dense", "top_k": 5}
    config_2 = {"strategy": "dense", "top_k": 10}

    key_1 = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_a,
        query="transformers attention",
        retrieval_config=config_1,
    )

    # Identical inputs produce identical key
    key_2 = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_a,
        query="transformers attention",
        retrieval_config=config_1,
    )
    assert key_1 == key_2

    # Reversed order of eligible documents produces identical key
    key_reversed = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_a_reversed,
        query="transformers attention",
        retrieval_config=config_1,
    )
    assert key_1 == key_reversed

    # Different user_id produces distinct key
    key_diff_user = RetrievalCache.make_key(
        user_id="user_999",
        eligible_documents=docs_a,
        query="transformers attention",
        retrieval_config=config_1,
    )
    assert key_1 != key_diff_user

    # Reindexing a document produces distinct key (logical invalidation)
    key_reindexed = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_b,
        query="transformers attention",
        retrieval_config=config_1,
    )
    assert key_1 != key_reindexed

    # Deleting a document produces distinct key (logical invalidation)
    key_deleted = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_c,
        query="transformers attention",
        retrieval_config=config_1,
    )
    assert key_1 != key_deleted

    # Different retrieval configuration produces distinct key
    key_diff_config = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_a,
        query="transformers attention",
        retrieval_config=config_2,
    )
    assert key_1 != key_diff_config

    # Different query produces distinct key
    key_diff_query = RetrievalCache.make_key(
        user_id="user_123",
        eligible_documents=docs_a,
        query="convolutional networks",
        retrieval_config=config_1,
    )
    assert key_1 != key_diff_query


def test_cache_hit_and_miss_telemetry():
    cache = RetrievalCache(max_entries=10)

    key = "sample_key_1"
    candidates = [{"text": "Chunk text", "score": 0.95, "document_id": 1, "chunk_index": 0}]

    assert cache.get(key) is None
    assert cache.stats()["misses"] == 1
    assert cache.stats()["hits"] == 0

    cache.set(key, candidates)
    assert cache.stats()["entries"] == 1

    hit_candidates = cache.get(key)
    assert hit_candidates == candidates
    assert cache.stats()["hits"] == 1
    assert cache.stats()["misses"] == 1
    assert cache.stats()["hit_ratio"] == 0.5

    cache.reset_stats()
    assert cache.stats()["hits"] == 0
    assert cache.stats()["misses"] == 0
    assert cache.stats()["entries"] == 1

    cache.clear()
    assert cache.stats()["entries"] == 0


def test_independent_deep_copies_prevent_caller_mutation():
    cache = RetrievalCache(max_entries=10)
    key = "mutation_test_key"

    original = [{"text": "Original text", "score": 0.8, "document_id": 10}]
    cache.set(key, original)

    # Mutate original caller list
    original[0]["text"] = "Corrupted text"
    original.append({"text": "Extra chunk"})

    fetched = cache.get(key)
    assert len(fetched) == 1
    assert fetched[0]["text"] == "Original text"

    # Mutate fetched result
    fetched[0]["text"] = "Mutated fetched text"
    fetched[0]["score"] = 0.0

    again = cache.get(key)
    assert again[0]["text"] == "Original text"
    assert again[0]["score"] == 0.8


def test_lru_eviction():
    cache = RetrievalCache(max_entries=2)

    cache.set("k1", [{"id": 1}])
    cache.set("k2", [{"id": 2}])
    assert cache.stats()["entries"] == 2
    assert cache.stats()["evictions"] == 0

    # Adding a 3rd item should evict k1 (oldest)
    cache.set("k3", [{"id": 3}])
    assert cache.stats()["entries"] == 2
    assert cache.stats()["evictions"] == 1
    assert cache.get("k1") is None
    assert cache.get("k2") is not None
    assert cache.get("k3") is not None

    # Accessing k2 moves it to MRU, so k3 becomes oldest
    cache.get("k2")
    cache.set("k4", [{"id": 4}])
    assert cache.get("k3") is None  # evicted
    assert cache.get("k2") is not None
    assert cache.get("k4") is not None


def test_concurrent_access_thread_safety():
    cache = RetrievalCache(max_entries=50)

    def worker(worker_id):
        for i in range(100):
            key = f"key_{worker_id}_{i % 10}"
            cache.set(key, [{"worker": worker_id, "iteration": i}])
            _ = cache.get(key)

    threads = [threading.Thread(target=worker, args=(tid,)) for tid in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    stats = cache.stats()
    assert stats["entries"] <= 50
    assert stats["hits"] + stats["misses"] > 0
