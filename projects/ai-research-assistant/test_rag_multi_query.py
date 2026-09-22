"""Automated test suite for Day 146: Multi-Query Retrieval and Decomposition."""

from unittest.mock import MagicMock
from backend.config import settings
from backend.services.query_decomposer import (
    MAX_SUBQUERIES,
    decompose_query,
    heuristic_decompose_query,
    decompose_query_with_llm
)
from backend.services.query_router import QueryType
from backend.services.rag_service import run_rag_pipeline
from backend.services.rag_context import build_rag_context
from backend.database import SessionLocal
from observability import RAGTrace


def test_heuristic_decomposition_rules():
    print("--- 1. Testing Heuristic Query Decomposition Rules ---")

    # Multi-dimensional comparison query
    q1 = "Compare Transformer and RNN architectures in terms of parallelization, long-range dependencies, and computational cost"
    subs1 = heuristic_decompose_query(q1)
    assert len(subs1) == 3, f"Expected 3 subqueries, got {len(subs1)}: {subs1}"
    assert any("parallelization" in s.lower() for s in subs1)
    assert any("long-range dependencies" in s.lower() for s in subs1)
    assert any("computational cost" in s.lower() for s in subs1)

    # Entity vs entity comparison
    q2 = "Compare BERT versus GPT"
    subs2 = heuristic_decompose_query(q2)
    assert len(subs2) == 2, f"Expected 2 subqueries, got {len(subs2)}: {subs2}"
    assert "BERT" in subs2[0]
    assert "GPT" in subs2[1]

    # Differences between X and Y
    q3 = "What are the differences between supervised learning and reinforcement learning?"
    subs3 = heuristic_decompose_query(q3)
    assert len(subs3) == 2, f"Expected 2 subqueries, got {len(subs3)}: {subs3}"

    # Simple factual query should not be decomposed
    q4 = "Which dataset was used for training?"
    subs4 = heuristic_decompose_query(q4)
    assert subs4 == [q4], f"Expected single query fallback, got {subs4}"

    # Empty / whitespace handling
    assert heuristic_decompose_query("") == []
    assert heuristic_decompose_query("   ") == []

    print("Heuristic decomposition patterns validated.")


def test_max_subqueries_capping():
    print("\n--- 2. Testing MAX_SUBQUERIES Capping ---")

    # Create a query with 6 dimensions
    long_q = "Compare Model A and Model B in terms of latency, throughput, memory, accuracy, robustness, and cost"
    subs = heuristic_decompose_query(long_q)
    assert len(subs) <= MAX_SUBQUERIES, f"Expected at most {MAX_SUBQUERIES}, got {len(subs)}"
    assert len(subs) == 4, f"Expected capped at 4, got {len(subs)}"

    # Decompose query wrapper also enforces max limit
    assert len(decompose_query(long_q)) <= MAX_SUBQUERIES
    print("Subquery capping at MAX_SUBQUERIES enforced.")


def test_llm_decomposition_with_mock():
    print("\n--- 3. Testing LLM Decomposition with Mocked Client ---")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"queries": ["Transformer parallelization", "RNN sequential computation"]}'
    mock_client.models.generate_content.return_value = mock_response

    q = "Compare Transformer vs RNN"
    subs = decompose_query_with_llm(q, mock_client)
    assert len(subs) == 2
    assert subs[0] == "Transformer parallelization"
    assert subs[1] == "RNN sequential computation"

    # Test JSON markdown backticks handling
    mock_response.text = '```json\n{"queries": ["Subquery A", "Subquery B", "Subquery C"]}\n```'
    subs_json = decompose_query_with_llm(q, mock_client)
    assert len(subs_json) == 3
    assert subs_json[0] == "Subquery A"

    # Test error fallback to heuristic
    mock_client.models.generate_content.side_effect = Exception("API rate limit")
    fallback_subs = decompose_query_with_llm("Compare Alpha versus Beta", mock_client)
    assert len(fallback_subs) == 2
    assert "Alpha" in fallback_subs[0]
    assert "Beta" in fallback_subs[1]

    print("LLM decomposition and fallback mechanism verified.")


def test_chunk_deduplication_and_matched_queries():
    print("\n--- 4. Testing Chunk Deduplication and Matched Queries ---")

    # Simulate chunks retrieved from 2 subqueries with overlap
    chunk_1 = {
        "text": "Self-attention enables parallel computation.",
        "score": 0.85,
        "vector_score": 0.85,
        "document_id": 10,
        "filename": "transformer.pdf",
        "chunk_index": 2,
        "matched_queries": ["Transformer parallelization"]
    }
    chunk_2_sub1 = {
        "text": "Recurrent connections hinder training parallelization.",
        "score": 0.70,
        "vector_score": 0.70,
        "document_id": 20,
        "filename": "rnn.pdf",
        "chunk_index": 1,
        "matched_queries": ["Transformer parallelization"]
    }
    chunk_2_sub2 = {
        "text": "Recurrent connections hinder training parallelization.",
        "score": 0.92,  # Higher score in subquery 2
        "vector_score": 0.92,
        "document_id": 20,
        "filename": "rnn.pdf",
        "chunk_index": 1,
        "matched_queries": ["RNN sequential computation"]
    }

    # Simulate deduplication logic
    deduped = {}
    for c in [chunk_1, chunk_2_sub1, chunk_2_sub2]:
        key = (c["document_id"], c["chunk_index"])
        if key not in deduped:
            deduped[key] = dict(c)
        else:
            existing = deduped[key]
            for sq in c["matched_queries"]:
                if sq not in existing["matched_queries"]:
                    existing["matched_queries"].append(sq)
            if c["score"] > existing["score"]:
                existing["score"] = c["score"]
                existing["vector_score"] = c["vector_score"]

    deduped_list = list(deduped.values())
    assert len(deduped_list) == 2, f"Expected 2 unique chunks, got {len(deduped_list)}"

    shared_chunk = next(c for c in deduped_list if c["document_id"] == 20)
    assert shared_chunk["score"] == 0.92, "Highest score should be retained"
    assert len(shared_chunk["matched_queries"]) == 2
    assert "Transformer parallelization" in shared_chunk["matched_queries"]
    assert "RNN sequential computation" in shared_chunk["matched_queries"]

    # Verify context builder preserves matched_queries
    context_res = build_rag_context(deduped_list)
    assert len(context_res["sources"]) == 2
    src_shared = next(s for s in context_res["sources"] if s["document_id"] == 20)
    assert "matched_queries" in src_shared
    assert len(src_shared["matched_queries"]) == 2

    print("Chunk deduplication, score preservation, and matched queries verified.")


def test_pipeline_multi_query_execution():
    print("\n--- 5. Testing Pipeline Multi-Query Execution ---")

    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"

        # Comparison query triggers multi-query retrieval
        comp_q = "Compare dense retrieval versus keyword retrieval in terms of recall and latency"
        res_comp = run_rag_pipeline(query=comp_q, user_id=user_id, db=db)
        assert res_comp["query_type"] == "comparison"
        assert "subqueries" in res_comp
        assert len(res_comp["subqueries"]) >= 2
        assert len(res_comp["subqueries"]) <= MAX_SUBQUERIES

        # Factual query does NOT trigger multi-query retrieval
        fact_q = "Which dataset was used for training?"
        res_fact = run_rag_pipeline(query=fact_q, user_id=user_id, db=db)
        assert res_fact["query_type"] == "factual"
        assert res_fact["subqueries"] == [fact_q]

        # Semantic query does NOT trigger multi-query retrieval
        sem_q = "Explain the intuition behind self-attention mechanisms"
        res_sem = run_rag_pipeline(query=sem_q, user_id=user_id, db=db)
        assert res_sem["query_type"] == "semantic"
        assert res_sem["subqueries"] == [sem_q]

        print("Pipeline multi-query conditional execution verified.")
    finally:
        db.close()


def test_multi_query_toggle_configuration():
    print("\n--- 6. Testing Multi-Query Feature Toggle ---")

    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"
        comp_q = "Compare Model A versus Model B"

        # Temporarily disable multi-query
        original_toggle = getattr(settings, "multi_query_enabled", True)
        try:
            settings.multi_query_enabled = False
            res = run_rag_pipeline(query=comp_q, user_id=user_id, db=db)
            assert res["subqueries"] == [comp_q], "When disabled, subqueries should only be [query]"
        finally:
            settings.multi_query_enabled = original_toggle

        print("Feature toggle behavior verified.")
    finally:
        db.close()


def test_security_and_tenant_isolation_with_multi_query():
    print("\n--- 7. Testing Security and Tenant Isolation ---")

    db = SessionLocal()
    try:
        isolated_user = "unauthorized_multi_query_user_999"
        comp_q = "Compare confidential budget and secret roadmap"
        res = run_rag_pipeline(query=comp_q, user_id=isolated_user, db=db)

        # Multi-query was generated, but 0 documents should be retrieved
        assert res["has_context"] is False
        assert len(res["sources"]) == 0
        assert "I couldn't find enough information" in res["answer"]
        print("Tenant isolation strictly enforced across all subqueries.")
    finally:
        db.close()


def test_observability_trace_subqueries():
    print("\n--- 8. Testing Observability Trace Subqueries ---")

    trace = RAGTrace(
        query="Compare A vs B",
        query_type="comparison",
        subqueries=["A features", "B features"]
    )
    assert trace.subqueries == ["A features", "B features"]
    assert trace.query_type == "comparison"
    print("Observability trace verified with subqueries.")


if __name__ == "__main__":
    test_heuristic_decomposition_rules()
    test_max_subqueries_capping()
    test_llm_decomposition_with_mock()
    test_chunk_deduplication_and_matched_queries()
    test_pipeline_multi_query_execution()
    test_multi_query_toggle_configuration()
    test_security_and_tenant_isolation_with_multi_query()
    test_observability_trace_subqueries()
    print("\n[SUCCESS] All Day 146 Multi-Query Retrieval Tests Passed!")
