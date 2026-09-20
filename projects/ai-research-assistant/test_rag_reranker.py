"""Automated test suite for Day 144: Retrieval Quality: Reranking."""

import pytest
from backend.config import settings
from backend.schemas.rag import Source, RAGResponse
from backend.services.rag_context import RetrievedChunk, build_rag_context
from backend.services.reranker import Reranker, CrossEncoderReranker, get_reranker
from backend.services.rag_service import run_rag_pipeline
from backend.database import SessionLocal


def test_reranker_interface_and_instantiation():
    print("--- 1. Testing Reranker Interface and Instantiation ---")
    reranker = get_reranker()
    assert isinstance(reranker, Reranker)
    assert isinstance(reranker, CrossEncoderReranker)
    print("Reranker interface and singleton verified.")


def test_cross_encoder_relevance_ordering():
    print("\n--- 2. Testing Cross-Encoder Relevance Ordering ---")
    reranker = get_reranker()
    query = "How does the Transformer encoder work?"

    # Candidate 1: Less relevant, but artificially higher vector score
    chunk_irrelevant = {
        "text": "Baking a chocolate cake requires sugar, cocoa powder, flour, and eggs mixed in a bowl.",
        "score": 0.95,
        "vector_score": 0.95,
        "document_id": 1,
        "filename": "recipes.pdf",
        "chunk_index": 0
    }

    # Candidate 2: Highly relevant, but lower initial vector score
    chunk_relevant = {
        "text": (
            "The Transformer encoder consists of a stack of 6 identical layers. Each layer has two sub-layers: "
            "a multi-head self-attention mechanism, and a position-wise fully connected feed-forward network."
        ),
        "score": 0.65,
        "vector_score": 0.65,
        "document_id": 2,
        "filename": "attention.pdf",
        "chunk_index": 4
    }

    candidates = [chunk_irrelevant, chunk_relevant]
    reranked = reranker.rerank(query=query, chunks=candidates, top_k=2)

    assert len(reranked) == 2
    # The relevant document must now be ranked #1
    assert reranked[0]["filename"] == "attention.pdf"
    assert reranked[1]["filename"] == "recipes.pdf"
    assert reranked[0]["reranker_score"] > reranked[1]["reranker_score"]
    print(
        f"Relevance ordering verified: Relevant score={reranked[0]['reranker_score']} vs Irrelevant score={reranked[1]['reranker_score']}"
    )


def test_score_preservation():
    print("\n--- 3. Testing Preservation of vector_score and reranker_score ---")
    reranker = get_reranker()
    query = "cryogenic qubit temperature"

    chunk = {
        "text": "Superconducting qubits operate at cryogenic temperatures around 15 millikelvin.",
        "score": 0.81,
        "vector_score": 0.81,
        "document_id": 3,
        "filename": "quantum.pdf",
        "chunk_index": 0
    }

    reranked = reranker.rerank(query=query, chunks=[chunk], top_k=1)
    res = reranked[0]

    # Check that vector_score is preserved
    assert res["vector_score"] == 0.81
    # Check that reranker_score is computed and recorded
    assert res["reranker_score"] is not None
    assert isinstance(res["reranker_score"], float)
    # Check that score reflects the reranker score
    assert res["score"] == res["reranker_score"]
    print(f"Scores preserved: vector_score={res['vector_score']}, reranker_score={res['reranker_score']}")


def test_candidate_truncation():
    print("\n--- 4. Testing Candidate Set Truncation (candidate_k -> top_k) ---")
    reranker = get_reranker()
    query = "quantum error correction"

    candidates = [
        {
            "text": f"Passage {i} discussing diverse aspects of physical systems and calculations.",
            "score": 0.70 + (i * 0.01),
            "vector_score": 0.70 + (i * 0.01),
            "document_id": i,
            "filename": f"doc_{i}.pdf",
            "chunk_index": 0
        }
        for i in range(10)
    ]

    reranked = reranker.rerank(query=query, chunks=candidates, top_k=3)
    assert len(reranked) == 3
    for i in range(len(reranked) - 1):
        assert reranked[i]["reranker_score"] >= reranked[i + 1]["reranker_score"]
    print("Candidate truncation from 10 to 3 verified with descending ordering.")


def test_context_builder_and_source_schema_integration():
    print("\n--- 5. Testing Context Builder and Source Schema with Dual Scores ---")
    chunks = [
        {
            "text": "The Transformer architecture relies on self-attention.",
            "score": 4.12,
            "vector_score": 0.88,
            "reranker_score": 4.12,
            "document_id": 12,
            "filename": "attention.pdf",
            "chunk_index": 4
        }
    ]

    rag_payload = build_rag_context(chunks)
    sources = rag_payload["sources"]
    cmap = rag_payload["citation_map"]

    assert len(sources) == 1
    src = sources[0]
    assert src["id"] == "S1"
    assert src["vector_score"] == 0.88
    assert src["reranker_score"] == 4.12
    assert src["score"] == 4.12

    assert "S1" in cmap
    assert cmap["S1"]["vector_score"] == 0.88
    assert cmap["S1"]["reranker_score"] == 4.12

    # Verify Pydantic Source schema model
    source_model = Source(**src)
    assert source_model.vector_score == 0.88
    assert source_model.reranker_score == 4.12
    print("Context builder and Source schema integration verified with dual scores.")


def test_reranker_configuration_toggle():
    print("\n--- 6. Testing Configurable Reranker Feature Toggle ---")
    db = SessionLocal()
    try:
        query = "What is the Transformer architecture?"
        user_id = "eval_benchmark_user"

        # 1. With reranker enabled
        settings.reranker_enabled = True
        out_enabled = run_rag_pipeline(query=query, user_id=user_id, db=db)
        if out_enabled["sources"]:
            assert out_enabled["sources"][0].get("reranker_score") is not None

        # 2. With reranker disabled (vector-only baseline)
        settings.reranker_enabled = False
        out_disabled = run_rag_pipeline(query=query, user_id=user_id, db=db)
        if out_disabled["sources"]:
            assert out_disabled["sources"][0].get("reranker_score") is None
            assert out_disabled["sources"][0]["vector_score"] is not None

        print("Reranker configuration toggle verified.")
    finally:
        settings.reranker_enabled = True
        db.close()


if __name__ == "__main__":
    test_reranker_interface_and_instantiation()
    test_cross_encoder_relevance_ordering()
    test_score_preservation()
    test_candidate_truncation()
    test_context_builder_and_source_schema_integration()
    test_reranker_configuration_toggle()
    print("\n[SUCCESS] All Day 144 Reranker Tests Passed!")
