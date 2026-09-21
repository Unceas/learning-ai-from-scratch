"""Automated test suite for Day 145: RAG Query Routing."""

from backend.config import settings
from backend.services.query_router import classify_query, get_retrieval_config, QueryType
from backend.services.rag_service import run_rag_pipeline
from backend.evaluation.dataset import EVAL_DATASET
from backend.database import SessionLocal
from observability import RAGTrace


def test_query_classification_rules():
    print("--- 1. Testing Query Classification Rules ---")

    # 1. Comparison queries
    comp_queries = [
        "Compare Transformer versus RNN architectures",
        "What is the difference between BERT and GPT?",
        "How does dense vector search differ from keyword retrieval?",
        "Is FlashAttention better than standard attention?",
        "Explain the trade-offs between dense search vs sparse search",
        "Method A vs Method B in terms of latency"
    ]
    for q in comp_queries:
        res = classify_query(q)
        assert res == QueryType.COMPARISON, f"Expected COMPARISON for '{q}', got {res}"

    # 2. Factual queries
    fact_queries = [
        "Which dataset was used for training?",
        "Where do superconducting qubits operate?",
        "When was the learning rate decay schedule applied?",
        "Who authored the foundational paper?",
        "How many warmup steps were used during training?",
        "At what temperature do superconducting qubits operate?",
        "What year was the dataset released?"
    ]
    for q in fact_queries:
        res = classify_query(q)
        assert res == QueryType.FACTUAL, f"Expected FACTUAL for '{q}', got {res}"

    # 3. Semantic queries
    sem_queries = [
        "Explain the intuition behind self-attention mechanisms",
        "What principles govern quantum superposition?",
        "Discuss the impact of climate emissions on global warming",
        "Why is document deduplication critical in ingestion pipelines?",
        "Describe the role of layer normalization in the encoder",
        "",
        "   "
    ]
    for q in sem_queries:
        res = classify_query(q)
        assert res == QueryType.SEMANTIC, f"Expected SEMANTIC for '{q}', got {res}"

    print("Query classification patterns verified across all archetypes.")


def test_retrieval_configuration_mapping():
    print("\n--- 2. Testing Retrieval Configuration Mapping ---")

    cfg_factual = get_retrieval_config(QueryType.FACTUAL)
    assert cfg_factual["candidate_k"] == 10
    assert cfg_factual["final_k"] == 3

    cfg_comp = get_retrieval_config(QueryType.COMPARISON)
    assert cfg_comp["candidate_k"] == 30
    assert cfg_comp["final_k"] == 8

    cfg_semantic = get_retrieval_config(QueryType.SEMANTIC)
    assert cfg_semantic["candidate_k"] == 20
    assert cfg_semantic["final_k"] == 5

    # String type handling & fallback
    assert get_retrieval_config("factual")["candidate_k"] == 10
    assert get_retrieval_config("comparison")["final_k"] == 8
    assert get_retrieval_config("unknown_type")["candidate_k"] == 20

    print("Retrieval configuration mapping verified.")


def test_pipeline_routing_integration():
    print("\n--- 3. Testing RAG Pipeline Routing Integration ---")
    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"

        # Factual query
        q_fact = "Which dataset was used for the experiment?"
        out_fact = run_rag_pipeline(query=q_fact, user_id=user_id, db=db)
        assert out_fact["query_type"] == "factual"
        assert out_fact["routing"]["candidate_k"] == 10
        assert out_fact["routing"]["final_k"] == 3

        # Comparison query
        q_comp = "How does dense vector search differ from keyword retrieval?"
        out_comp = run_rag_pipeline(query=q_comp, user_id=user_id, db=db)
        assert out_comp["query_type"] == "comparison"
        assert out_comp["routing"]["candidate_k"] == 30
        assert out_comp["routing"]["final_k"] == 8

        # Semantic query
        q_sem = "What principles govern quantum superposition?"
        out_sem = run_rag_pipeline(query=q_sem, user_id=user_id, db=db)
        assert out_sem["query_type"] == "semantic"
        assert out_sem["routing"]["candidate_k"] == 20
        assert out_sem["routing"]["final_k"] == 5

        print("Pipeline query routing execution verified.")
    finally:
        db.close()


def test_observability_trace_recording():
    print("\n--- 4. Testing Observability Trace Recording ---")
    trace = RAGTrace(
        query="Compare Model A vs Model B",
        query_type="comparison",
        candidate_k=30,
        final_k=8
    )
    assert trace.query_type == "comparison"
    assert trace.candidate_k == 30
    assert trace.final_k == 8
    assert trace.total_ms == 0.0
    print("Observability trace schema verified with routing metadata.")


def test_security_and_tenant_isolation_with_routing():
    print("\n--- 5. Testing Security and Tenant Isolation Preservation ---")
    db = SessionLocal()
    try:
        # A non-existent user or user with 0 documents should return empty context regardless of query type
        empty_user = "non_existent_isolated_user_xyz"
        comp_query = "Compare all confidential documents vs public documents"
        res = run_rag_pipeline(query=comp_query, user_id=empty_user, db=db)

        # Router classifies as comparison, but security strictly isolates to 0 chunks
        assert res["query_type"] == "comparison"
        assert res["has_context"] is False
        assert len(res["sources"]) == 0
        print("Security boundary verified: routing does not bypass document ownership.")
    finally:
        db.close()


def test_eval_dataset_query_type_coverage():
    print("\n--- 6. Testing Evaluation Dataset Query Type Coverage ---")
    assert len(EVAL_DATASET) == 15

    types_found = {item.get("type") for item in EVAL_DATASET}
    assert "semantic" in types_found
    assert "factual" in types_found
    assert "comparison" in types_found

    semantic_count = sum(1 for item in EVAL_DATASET if item.get("type") == "semantic")
    factual_count = sum(1 for item in EVAL_DATASET if item.get("type") == "factual")
    comp_count = sum(1 for item in EVAL_DATASET if item.get("type") == "comparison")

    print(f"Dataset coverage: Semantic={semantic_count}, Factual={factual_count}, Comparison={comp_count}")
    assert semantic_count > 0 and factual_count > 0 and comp_count > 0
    print("Evaluation dataset typing verified.")


if __name__ == "__main__":
    test_query_classification_rules()
    test_retrieval_configuration_mapping()
    test_pipeline_routing_integration()
    test_observability_trace_recording()
    test_security_and_tenant_isolation_with_routing()
    test_eval_dataset_query_type_coverage()
    print("\n[SUCCESS] All Day 145 Query Routing Tests Passed!")
