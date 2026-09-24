"""Automated test suite for Day 147: Hybrid Retrieval with BM25 and Reciprocal Rank Fusion (RRF)."""

from typing import Any, Dict
from unittest.mock import MagicMock
from backend.config import settings
from backend.services.keyword_retriever import KeywordRetriever
from backend.services.rank_fusion import reciprocal_rank_fusion
from backend.services.hybrid_retriever import HybridRetriever
from backend.services.reranker import get_reranker
from backend.services.rag_service import run_rag_pipeline
from backend.evaluation.dataset import HYBRID_EVAL_CASES
from backend.database import SessionLocal
from backend.models import Document
from retrieval import db_retrieve, db_keyword_retrieve, db_hybrid_retrieve


class MockChunk:
    def __init__(self, doc_id: int, chunk_idx: int, text: str, name: str = ""):
        self.document_id = doc_id
        self.chunk_index = chunk_idx
        self.text = text
        self.name = name or f"Doc{doc_id}_{chunk_idx}"

    def __repr__(self):
        return f"<MockChunk {self.name} doc={self.document_id}:{self.chunk_index}>"


def test_bm25_exact_term_retrieval():
    print("--- 1. Testing BM25 Exact Term Retrieval ---")

    corpus = [
        {"document_id": 1, "chunk_index": 0, "text": "This RFC 7231 document specifies HTTP/1.1 semantics and content negotiation."},
        {"document_id": 2, "chunk_index": 0, "text": "Deep residual learning for image recognition using ResNet-50 architecture."},
        {"document_id": 3, "chunk_index": 0, "text": "Low-rank adaptation LoRA freezes pre-trained model weights and injects trainable matrices."},
        {"document_id": 4, "chunk_index": 0, "text": "Attention mechanisms allow models to process sequence dependencies without recurrence."}
    ]

    retriever = KeywordRetriever(corpus)

    # Search exact term: "RFC 7231"
    res1 = retriever.retrieve("RFC 7231", top_k=2)
    assert len(res1) >= 1
    assert res1[0]["chunk"]["document_id"] == 1
    assert "RFC 7231" in res1[0]["chunk"]["text"]
    assert res1[0]["score"] > 0.0

    # Search acronym: "LoRA"
    res2 = retriever.retrieve("LoRA", top_k=2)
    assert len(res2) >= 1
    assert res2[0]["chunk"]["document_id"] == 3
    assert "LoRA" in res2[0]["chunk"]["text"]

    # Search model name: "ResNet-50"
    res3 = retriever.retrieve("ResNet-50", top_k=2)
    assert len(res3) >= 1
    assert res3[0]["chunk"]["document_id"] == 2
    assert "ResNet-50" in res3[0]["chunk"]["text"]

    # Search non-existent keyword returns empty when filter_zero=True
    res_none = retriever.retrieve("NonExistentTermXYZ999", top_k=5)
    assert len(res_none) == 0

    print("BM25 exact-term and acronym matching validated.")


def test_dense_retrieval_baseline():
    print("\n--- 2. Testing Dense Retrieval Baseline ---")
    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"
        res = db_retrieve(db=db, user_id=user_id, query="self-attention mechanism", top_k=5)
        assert isinstance(res, list)
        if res:
            assert "text" in res[0]
            assert "score" in res[0]
            assert "document_id" in res[0]
        print(f"Dense retrieval functional (retrieved {len(res)} chunks).")
    finally:
        db.close()


def test_reciprocal_rank_fusion_cumulative_scoring():
    print("\n--- 3. Testing Reciprocal Rank Fusion & Cumulative Scoring ---")

    # Day 147 explicit test specification:
    # Dense: A, B, C, D
    # BM25:  C, E, A, F
    # RRF:   A & C should receive cumulative rank-fusion scores and rank top.
    chunk_a = MockChunk(1, 0, "Chunk A text", "A")
    chunk_b = MockChunk(2, 0, "Chunk B text", "B")
    chunk_c = MockChunk(3, 0, "Chunk C text", "C")
    chunk_d = MockChunk(4, 0, "Chunk D text", "D")
    chunk_e = MockChunk(5, 0, "Chunk E text", "E")
    chunk_f = MockChunk(6, 0, "Chunk F text", "F")

    dense_results = [
        {"chunk": chunk_a, "score": 0.95},
        {"chunk": chunk_b, "score": 0.85},
        {"chunk": chunk_c, "score": 0.75},
        {"chunk": chunk_d, "score": 0.65},
    ]

    bm25_results = [
        {"chunk": chunk_c, "score": 14.2},
        {"chunk": chunk_e, "score": 10.1},
        {"chunk": chunk_a, "score": 8.5},
        {"chunk": chunk_f, "score": 5.0},
    ]

    k = 60
    fused = reciprocal_rank_fusion([dense_results, bm25_results], k=k)

    # Calculations:
    # A in Dense: rank 1 -> 1 / 61
    # A in BM25:  rank 3 -> 1 / 63
    # Expected A score = 1/61 + 1/63
    expected_score_a = (1.0 / 61) + (1.0 / 63)

    # C in Dense: rank 3 -> 1 / 63
    # C in BM25:  rank 1 -> 1 / 61
    # Expected C score = 1/63 + 1/61
    expected_score_c = (1.0 / 63) + (1.0 / 61)

    # B in Dense: rank 2 -> 1 / 62
    expected_score_b = 1.0 / 62

    # E in BM25: rank 2 -> 1 / 62
    expected_score_e = 1.0 / 62

    top_two_names = {fused[0]["chunk"].name, fused[1]["chunk"].name}
    assert top_two_names == {"A", "C"}, f"Expected top two to be A and C, got {top_two_names}"

    score_map = {item["chunk"].name: item["score"] for item in fused}
    assert abs(score_map["A"] - expected_score_a) < 1e-6
    assert abs(score_map["C"] - expected_score_c) < 1e-6
    assert abs(score_map["B"] - expected_score_b) < 1e-6
    assert abs(score_map["E"] - expected_score_e) < 1e-6

    # Verify cumulative boost
    assert score_map["A"] > score_map["B"]
    assert score_map["C"] > score_map["E"]

    print("RRF cumulative rank-fusion scoring matches exact mathematical formula.")


def test_chunk_deduplication_and_metadata_preservation():
    print("\n--- 4. Testing Chunk Deduplication and Metadata Preservation ---")

    chunk_shared_dense = {
        "document_id": 42,
        "chunk_index": 3,
        "filename": "quantum.pdf",
        "text": "Superconducting qubits operate at cryogenic temperatures.",
        "vector_score": 0.89,
        "matched_queries": ["qubit temperature"]
    }
    chunk_shared_bm25 = {
        "document_id": 42,
        "chunk_index": 3,
        "filename": "quantum.pdf",
        "text": "Superconducting qubits operate at cryogenic temperatures.",
        "matched_queries": ["cryogenic operations"]
    }

    fused = reciprocal_rank_fusion([
        [{"chunk": chunk_shared_dense, "score": 0.89}],
        [{"chunk": chunk_shared_bm25, "score": 12.0}]
    ])

    assert len(fused) == 1, "Duplicate chunk across result sets must be merged"
    merged = fused[0]["chunk"]
    assert merged["document_id"] == 42
    assert merged["chunk_index"] == 3
    assert merged["filename"] == "quantum.pdf"
    assert merged["vector_score"] == 0.89
    assert "qubit temperature" in merged["matched_queries"]
    assert "cryogenic operations" in merged["matched_queries"]
    print("Deduplication and metadata preservation verified.")


def test_hybrid_retriever_class():
    print("\n--- 5. Testing HybridRetriever Coordinator Class ---")

    mock_dense = MagicMock()
    mock_dense.retrieve.return_value = [
        {"chunk": {"document_id": 1, "chunk_index": 0, "text": "Dense Hit 1"}, "score": 0.9},
        {"chunk": {"document_id": 2, "chunk_index": 0, "text": "Dense Hit 2"}, "score": 0.8},
    ]

    mock_keyword = MagicMock()
    mock_keyword.retrieve.return_value = [
        {"chunk": {"document_id": 2, "chunk_index": 0, "text": "Dense Hit 2"}, "score": 15.0},
        {"chunk": {"document_id": 3, "chunk_index": 0, "text": "Keyword Hit 3"}, "score": 12.0},
    ]

    hybrid = HybridRetriever(dense_retriever=mock_dense, keyword_retriever=mock_keyword, rrf_k=60)
    results = hybrid.retrieve(query="Test Query", dense_k=5, keyword_k=5, final_k=2)

    assert len(results) == 2
    # Document 2 appeared in both, so it should rank first
    assert results[0]["chunk"]["document_id"] == 2
    print("HybridRetriever coordinator executed and ranked multi-source hits correctly.")


def test_user_isolation_and_security():
    print("\n--- 6. Testing User Isolation and Security ---")

    db = SessionLocal()
    try:
        unauthorized_user = "unauthorized_hybrid_user_999"
        res_kw = db_keyword_retrieve(db=db, user_id=unauthorized_user, query="attention", top_k=5)
        res_hybrid = db_hybrid_retrieve(db=db, user_id=unauthorized_user, query="attention", top_k=5)

        assert len(res_kw) == 0, "Unauthorized user must not retrieve any keyword chunks"
        assert len(res_hybrid) == 0, "Unauthorized user must not retrieve any hybrid chunks"
        print("Tenant isolation strictly enforced for keyword and hybrid search.")
    finally:
        db.close()


def test_processing_and_failed_documents_excluded():
    print("\n--- 7. Testing Processing and Failed Documents Are Not Searchable ---")

    db = SessionLocal()
    try:
        user_id = "status_filter_test_user"

        # Create processing doc and failed doc
        doc_proc = Document(
            user_id=user_id,
            filename="proc.pdf",
            file_hash="hash_proc_123",
            status="processing"
        )
        doc_fail = Document(
            user_id=user_id,
            filename="fail.pdf",
            file_hash="hash_fail_123",
            status="failed"
        )
        db.add(doc_proc)
        db.add(doc_fail)
        db.commit()

        # Both keyword and dense retrieval must return 0 results because status is not 'indexed'
        kw_res = db_keyword_retrieve(db=db, user_id=user_id, query="anything", top_k=5)
        dense_res = db_retrieve(db=db, user_id=user_id, query="anything", top_k=5)
        hybrid_res = db_hybrid_retrieve(db=db, user_id=user_id, query="anything", top_k=5)

        assert len(kw_res) == 0
        assert len(dense_res) == 0
        assert len(hybrid_res) == 0

        # Clean up
        db.delete(doc_proc)
        db.delete(doc_fail)
        db.commit()
        print("Processing and failed documents are strictly excluded from retrieval.")
    finally:
        db.close()


def test_hybrid_results_passed_to_reranker():
    print("\n--- 8. Testing Hybrid Results Passed to CrossEncoder Reranker ---")

    reranker = get_reranker()

    fused_candidates = [
        {"chunk": {"document_id": 1, "chunk_index": 0, "text": "Attention is all you need for sequence models."}, "score": 0.032},
        {"chunk": {"document_id": 2, "chunk_index": 0, "text": "Recurrent neural networks process sequential tokens one by one."}, "score": 0.016},
        {"chunk": {"document_id": 3, "chunk_index": 0, "text": "Convolutional layers capture local spatial hierarchies."}, "score": 0.015}
    ]

    reranked = reranker.rerank(query="self-attention in transformers", chunks=fused_candidates, top_k=2)
    assert len(reranked) == 2
    assert "reranker_score" in reranked[0]
    assert "Attention" in reranked[0]["text"]
    print("Reranker successfully consumes wrapped RRF hybrid candidates.")


def test_multi_query_and_hybrid_integration():
    print("\n--- 9. Testing Multi-Query and Hybrid Integration ---")

    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"
        comp_q = "Compare Transformer vs RNN in terms of parallelization and long-range dependencies"

        pipeline_res = run_rag_pipeline(query=comp_q, user_id=user_id, db=db)

        assert pipeline_res["query_type"] == "comparison"
        assert len(pipeline_res["subqueries"]) >= 2

        # Check deduplication in sources
        sources = pipeline_res["sources"]
        seen_keys = set()
        for s in sources:
            key = (s.get("document_id"), s.get("chunk_index"))
            assert key not in seen_keys, f"Duplicate source found in multi-query hybrid pipeline: {key}"
            seen_keys.add(key)

        print("Multi-query + hybrid retrieval correctly avoids duplicate chunks.")
    finally:
        db.close()


def test_hybrid_evaluation_cases_coverage():
    print("\n--- 10. Testing Hybrid Evaluation Cases Coverage ---")

    assert len(HYBRID_EVAL_CASES) == 4
    categories = {item["category"] for item in HYBRID_EVAL_CASES}
    assert "exact_terminology" in categories
    assert "acronyms" in categories
    assert "semantic_question" in categories
    assert "paper_entity_names" in categories

    for case in HYBRID_EVAL_CASES:
        assert "question" in case and case["question"]
        assert "expected_documents" in case and len(case["expected_documents"]) > 0
        assert "expected_topics" in case and len(case["expected_topics"]) > 0
        assert "advantage" in case

    print("Hybrid evaluation dataset verified across all retrieval advantage archetypes.")


if __name__ == "__main__":
    test_bm25_exact_term_retrieval()
    test_dense_retrieval_baseline()
    test_reciprocal_rank_fusion_cumulative_scoring()
    test_chunk_deduplication_and_metadata_preservation()
    test_hybrid_retriever_class()
    test_user_isolation_and_security()
    test_processing_and_failed_documents_excluded()
    test_hybrid_results_passed_to_reranker()
    test_multi_query_and_hybrid_integration()
    test_hybrid_evaluation_cases_coverage()
    print("\n[SUCCESS] All Day 147 Hybrid Retrieval Tests Passed!")
