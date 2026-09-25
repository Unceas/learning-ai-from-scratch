"""Automated test suite for Day 148: Query Expansion and HyDE (Hypothetical Document Embeddings)."""

from unittest.mock import MagicMock
from backend.config import settings
from backend.services.query_expander import (
    MAX_EXPANDED_QUERIES,
    QueryExpander,
    LLMQueryExpander,
    heuristic_expand_query,
    expand_query,
    deduplicate_queries,
    normalize_query
)
from backend.services.hyde import HyDE
from backend.services.query_router import QueryType
from backend.services.rag_service import run_rag_pipeline
from backend.evaluation.dataset import EXPANSION_HYDE_EVAL_CASES
from backend.database import SessionLocal


def test_query_normalization_and_deduplication():
    print("--- 1. Testing Query Normalization & Deduplication ---")

    assert normalize_query("  What   is   LoRA?  ") == "what is lora?"
    assert normalize_query("TRANSFORMER\nattention") == "transformer attention"

    raw_queries = [
        "What is LoRA?",
        "what is lora?",
        "  WHAT IS LORA?  ",
        "low-rank adaptation",
        "Low-Rank Adaptation",
        "low-rank adaptation parameter-efficient fine-tuning"
    ]
    deduped = deduplicate_queries(raw_queries)
    assert len(deduped) == 3
    assert deduped[0] == "What is LoRA?"
    assert deduped[1] == "low-rank adaptation"
    assert deduped[2] == "low-rank adaptation parameter-efficient fine-tuning"
    print("Normalization and deduplication verified.")


def test_heuristic_query_expansion():
    print("\n--- 2. Testing Heuristic Query Expansion Fallback ---")

    # Terminology mismatch query
    q1 = "How do transformers remember things from far away in a sentence?"
    exp1 = heuristic_expand_query(q1)
    assert len(exp1) >= 1
    assert len(exp1) <= MAX_EXPANDED_QUERIES
    assert any("long-range" in a.lower() or "dependency" in a.lower() for a in exp1)

    # Acronym query
    q2 = "What does LoRA change in fine-tuning?"
    exp2 = heuristic_expand_query(q2)
    assert len(exp2) >= 1
    assert any("low-rank" in a.lower() or "adaptation" in a.lower() for a in exp2)

    # Empty / whitespace handling
    assert heuristic_expand_query("") == []
    assert heuristic_expand_query("   ") == []

    print("Heuristic expansion rules verified.")


def test_llm_query_expander_with_mock():
    print("\n--- 3. Testing LLMQueryExpander with Mock & Error Handling ---")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = {
        "queries": [
            "Transformer long-range dependency modeling",
            "self-attention sequence dependency mechanisms",
            "redundant extra query 3"
        ]
    }

    expander = LLMQueryExpander(llm=mock_llm)
    q = "How do transformers handle distant tokens?"
    res = expander.expand(q)

    # Verify capped to MAX_EXPANDED_QUERIES
    assert len(res) == MAX_EXPANDED_QUERIES
    assert res[0] == "Transformer long-range dependency modeling"
    assert res[1] == "self-attention sequence dependency mechanisms"

    # Test JSON string response parsing
    mock_llm.generate.return_value = '```json\n{"queries": ["Alt A", "Alt B"]}\n```'
    res_str = expander.expand(q)
    assert len(res_str) == 2
    assert res_str[0] == "Alt A"

    # Test error fallback to heuristic
    mock_llm.generate.side_effect = Exception("LLM Provider Timeout")
    res_fallback = expander.expand("What is LoRA?")
    assert len(res_fallback) >= 1
    assert any("low-rank" in s.lower() for s in res_fallback)

    print("LLM query expansion and fallback mechanisms verified.")


def test_expand_query_preserves_original_query():
    print("\n--- 4. Testing Original Query Preservation ---")

    original_q = "How do models remember distant tokens?"
    expanded_set = expand_query(original_q)

    # The user's query must ALWAYS be at index 0
    assert len(expanded_set) >= 2
    assert expanded_set[0] == original_q, "Original query must be preserved as primary search query"

    # All queries must be unique
    normalized_keys = [normalize_query(q) for q in expanded_set]
    assert len(normalized_keys) == len(set(normalized_keys))

    print("Original query preservation confirmed.")


def test_hyde_hypothesis_generation_and_embedding():
    print("\n--- 5. Testing HyDE Hypothesis Generation & Embedding ---")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = (
        "Self-attention allows the Transformer to compute direct connections between all tokens in a sequence, "
        "enabling robust modeling of long-range dependencies regardless of position."
    )

    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1, 0.2, 0.3, 0.4]

    hyde = HyDE(llm=mock_llm, embedding_model=mock_embedder)

    query = "How does attention capture long-range dependencies?"
    hypothesis = hyde.generate_hypothesis(query)
    assert len(hypothesis) > 20
    assert "Self-attention" in hypothesis

    embedding = hyde.embed_hypothesis(hypothesis)
    assert embedding == [0.1, 0.2, 0.3, 0.4]

    # Test fallback hypothesis when LLM is unavailable
    hyde_fallback = HyDE(llm=None, embedding_model=mock_embedder)
    fallback_hypo = hyde_fallback.generate_hypothesis("What is LoRA?")
    assert "Low-Rank Adaptation" in fallback_hypo or "LoRA" in fallback_hypo

    print("HyDE hypothesis generation and embedding verified.")


def test_hyde_security_and_hallucination_guard():
    print("\n--- 6. Testing HyDE Security Boundary & Hallucination Guard ---")

    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Hypothetical fictional hallucinated research paper text XYZ-999"

    mock_vector_store = MagicMock()
    mock_vector_store.search.return_value = {
        "documents": [["Actual indexed document passage from attention.pdf."]],
        "metadatas": [[{"document_id": 1, "filename": "attention.pdf", "chunk_index": 0}]],
        "distances": [[0.15]]
    }

    hyde = HyDE(llm=mock_llm)
    candidates = hyde.retrieve(
        query="Explain self-attention",
        user_id="authorized_user_1",
        document_ids=[1],
        vector_store=mock_vector_store,
        top_k=3
    )

    # 1. Security: vector_store.search must be scoped strictly to user_id and document_ids
    mock_vector_store.search.assert_called_once()
    call_kwargs = mock_vector_store.search.call_args[1]
    assert call_kwargs["user_id"] == "authorized_user_1"
    assert call_kwargs["document_ids"] == [1]

    # 2. Hallucination guard: candidate chunk text must be REAL document text, NOT the hypothesis!
    assert len(candidates) == 1
    assert candidates[0]["text"] == "Actual indexed document passage from attention.pdf."
    assert "XYZ-999" not in candidates[0]["text"]
    assert "hyde:" in candidates[0]["matched_queries"][0]

    # 3. Security: Empty document IDs returns empty list immediately
    empty_candidates = hyde.retrieve(
        query="Explain self-attention",
        user_id="authorized_user_1",
        document_ids=[],
        vector_store=mock_vector_store,
        top_k=3
    )
    assert len(empty_candidates) == 0

    print("HyDE tenant isolation and hallucination guards confirmed.")


def test_pipeline_integration_with_expansion_and_hyde():
    print("\n--- 7. Testing Pipeline Integration with Expansion and HyDE ---")

    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"

        # Semantic query triggers query expansion + HyDE
        sem_q = "How do transformers remember things from far away in a sentence?"
        res_sem = run_rag_pipeline(query=sem_q, user_id=user_id, db=db)

        assert res_sem["query_type"] == "semantic"
        assert "expanded_queries" in res_sem
        assert len(res_sem["expanded_queries"]) >= 1
        assert res_sem["used_hyde"] is True

        # Factual query triggers query expansion, but NOT HyDE
        fact_q = "Which dataset was used for training?"
        res_fact = run_rag_pipeline(query=fact_q, user_id=user_id, db=db)
        assert res_fact["query_type"] == "factual"
        assert res_fact["used_hyde"] is False

        # Verify source grounding: all sources have valid document_id
        for src in res_sem["sources"]:
            assert src["document_id"] is not None
            assert src["filename"] != "Unknown"

        print("Pipeline integration across semantic and factual queries verified.")
    finally:
        db.close()


def test_feature_flags_toggle():
    print("\n--- 8. Testing Feature Flags Toggle ---")

    db = SessionLocal()
    try:
        user_id = "eval_benchmark_user"
        sem_q = "How does self-attention capture long-range dependencies?"

        orig_exp = settings.query_expansion_enabled
        orig_hyde = settings.hyde_enabled
        try:
            settings.query_expansion_enabled = False
            settings.hyde_enabled = False

            res = run_rag_pipeline(query=sem_q, user_id=user_id, db=db)
            assert res["expanded_queries"] == []
            assert res["used_hyde"] is False
        finally:
            settings.query_expansion_enabled = orig_exp
            settings.hyde_enabled = orig_hyde

        print("Feature flags toggles verified.")
    finally:
        db.close()


def test_expansion_and_hyde_evaluation_dataset_coverage():
    print("\n--- 9. Testing Evaluation Dataset Coverage ---")

    assert len(EXPANSION_HYDE_EVAL_CASES) == 4
    categories = {item["category"] for item in EXPANSION_HYDE_EVAL_CASES}
    assert "short_query" in categories
    assert "terminology_mismatch" in categories
    assert "exact_technical_query" in categories
    assert "complex_query" in categories

    for case in EXPANSION_HYDE_EVAL_CASES:
        assert case["question"].strip()
        assert len(case["expected_documents"]) > 0
        assert len(case["expected_topics"]) > 0
        assert case["advantage"] in ["query_expansion", "hyde", "hybrid", "expansion_and_hyde"]

    print("Evaluation cases coverage verified across all advantage archetypes.")


if __name__ == "__main__":
    test_query_normalization_and_deduplication()
    test_heuristic_query_expansion()
    test_llm_query_expander_with_mock()
    test_expand_query_preserves_original_query()
    test_hyde_hypothesis_generation_and_embedding()
    test_hyde_security_and_hallucination_guard()
    test_pipeline_integration_with_expansion_and_hyde()
    test_feature_flags_toggle()
    test_expansion_and_hyde_evaluation_dataset_coverage()
    print("\n[SUCCESS] All Day 148 Query Expansion & HyDE Tests Passed!")
