"""Comprehensive test suite for Day 142: RAG Source Citations and Citation Validation."""

import asyncio
import uuid
import httpx

from backend.main import app
from backend.schemas.rag import Source, RAGResponse, DocumentGroupedSource
from backend.services.rag_context import (
    RetrievedChunk,
    build_context,
    build_rag_context,
    validate_citations
)
from backend.services.rag_service import run_rag_pipeline
from test_retrieval_reliability import make_test_pdf


def test_schema_contract():
    print("--- 1. Testing Source and RAGResponse Schemas ---")
    source_obj = Source(
        id="S1",
        document_id=12,
        filename="attention.pdf",
        chunk_index=4,
        score=0.91
    )
    assert source_obj.id == "S1"
    assert source_obj.document_id == 12
    assert source_obj.filename == "attention.pdf"
    assert source_obj.chunk_index == 4
    assert source_obj.score == 0.91

    rag_resp = RAGResponse(
        answer="The Transformer encoder processes tokens via self-attention. [S1]",
        sources=[source_obj],
        citation_map={"S1": source_obj}
    )
    assert rag_resp.answer.startswith("The Transformer")
    assert len(rag_resp.sources) == 1
    assert rag_resp.sources[0].id == "S1"
    print("Source and RAGResponse schema contracts verified.")


def test_stable_identifier_generation():
    print("\n--- 2. Testing Stable [S1], [S2] Source Identifier Generation ---")
    chunks = [
        {"text": "The Transformer architecture relies on self-attention.", "score": 0.92, "document_id": 12, "filename": "attention.pdf", "chunk_index": 4},
        {"text": "The encoder consists of a stack of identical layers.", "score": 0.88, "document_id": 12, "filename": "attention.pdf", "chunk_index": 7},
    ]
    rag_payload = build_rag_context(chunks)

    # Check context formatting
    context = rag_payload["context"]
    assert "[S1]" in context
    assert "File: attention.pdf" in context
    assert "Chunk: 4" in context
    assert "The Transformer architecture relies on self-attention." in context

    assert "[S2]" in context
    assert "Chunk: 7" in context
    assert "The encoder consists of a stack of identical layers." in context

    # Check sources list IDs
    assert len(rag_payload["sources"]) == 2
    assert rag_payload["sources"][0]["id"] == "S1"
    assert rag_payload["sources"][1]["id"] == "S2"
    print("Stable [S1], [S2] identifiers and context blocks verified.")


def test_citation_map_construction():
    print("\n--- 3. Testing Citation Map Construction ---")
    chunks = [
        {"text": "Chunk text A", "score": 0.91, "document_id": 12, "filename": "attention.pdf", "chunk_index": 4},
        {"text": "Chunk text B", "score": 0.87, "document_id": 12, "filename": "attention.pdf", "chunk_index": 7},
    ]
    rag_payload = build_rag_context(chunks)
    cmap = rag_payload["citation_map"]

    assert "S1" in cmap
    assert cmap["S1"]["document_id"] == 12
    assert cmap["S1"]["filename"] == "attention.pdf"
    assert cmap["S1"]["chunk_index"] == 4
    assert cmap["S1"]["score"] == 0.91

    assert "S2" in cmap
    assert cmap["S2"]["document_id"] == 12
    assert cmap["S2"]["filename"] == "attention.pdf"
    assert cmap["S2"]["chunk_index"] == 7
    assert cmap["S2"]["score"] == 0.87
    print("Citation map construction verified.")


def test_citation_validation():
    print("\n--- 4. Testing Citation Validation and Hallucination Detection ---")
    sources = [
        {"id": "S1", "document_id": 10, "filename": "paper_a.pdf", "chunk_index": 0},
        {"id": "S2", "document_id": 20, "filename": "paper_b.pdf", "chunk_index": 1}
    ]

    # Valid citations
    answer_valid = "According to findings, method A works best [S1] and method B confirms it [S2]."
    res_valid = validate_citations(answer_valid, sources)
    assert res_valid["is_valid"] is True
    assert res_valid["valid_citations"] == ["[S1]", "[S2]"]
    assert res_valid["invalid_citations"] == []

    # Invalid hallucinated citations
    answer_invalid = "The method achieves 99% accuracy [S1][S2][S99]."
    res_invalid = validate_citations(answer_invalid, sources)
    assert res_invalid["is_valid"] is False
    assert res_invalid["valid_citations"] == ["[S1]", "[S2]"]
    assert "[S99]" in res_invalid["invalid_citations"]

    # Multiple out-of-bounds citations
    answer_multiple_invalid = "Recent breakthroughs indicate quantum dominance [S4][S99]."
    res_multi = validate_citations(answer_multiple_invalid, sources)
    assert res_multi["is_valid"] is False
    assert "[S4]" in res_multi["invalid_citations"]
    assert "[S99]" in res_multi["invalid_citations"]
    print("Citation validation correctly identified valid and invalid markers.")


def test_source_deduplication_and_grouping():
    print("\n--- 5. Testing Source Deduplication & Grouping by Document ---")
    chunks = [
        {"text": "attention chunk 4", "score": 0.95, "document_id": 12, "filename": "attention.pdf", "chunk_index": 4},
        {"text": "attention chunk 5", "score": 0.90, "document_id": 12, "filename": "attention.pdf", "chunk_index": 5},
        {"text": "attention chunk 8", "score": 0.85, "document_id": 12, "filename": "attention.pdf", "chunk_index": 8},
        {"text": "another chunk 2", "score": 0.80, "document_id": 15, "filename": "another.pdf", "chunk_index": 2},
    ]
    rag_payload = build_rag_context(chunks)
    doc_sources = rag_payload["document_sources"]

    # 4 chunks across 2 documents
    assert len(rag_payload["sources"]) == 4
    assert len(doc_sources) == 2

    # Grouped chunks
    docs_by_name = {d["filename"]: d for d in doc_sources}
    assert "attention.pdf" in docs_by_name
    assert docs_by_name["attention.pdf"]["document_id"] == 12
    assert docs_by_name["attention.pdf"]["chunks"] == [4, 5, 8]

    assert "another.pdf" in docs_by_name
    assert docs_by_name["another.pdf"]["document_id"] == 15
    assert docs_by_name["another.pdf"]["chunks"] == [2]
    print("Document grouping with chunk lists verified.")


def test_citation_correctness_and_unsupported_questions():
    print("\n--- 6. Testing Citation Correctness on Queries & Unsupported Fallback ---")
    # Paper A and Paper B setup
    chunks = [
        {"text": "Paper A says X: solar panels generate clean electrical energy.", "score": 0.95, "document_id": 101, "filename": "paper_a.pdf", "chunk_index": 0},
        {"text": "Paper B says Y: wind turbines produce renewable mechanical energy.", "score": 0.90, "document_id": 102, "filename": "paper_b.pdf", "chunk_index": 0},
    ]
    rag_payload = build_rag_context(chunks)

    # Simulated LLM answers
    ans_a = "Paper A explains that solar panels produce clean energy. [S1]"
    val_a = validate_citations(ans_a, rag_payload["citation_map"])
    assert "[S1]" in val_a["valid_citations"]
    assert len(val_a["invalid_citations"]) == 0

    ans_b = "Paper B demonstrates wind turbine mechanics. [S2]"
    val_b = validate_citations(ans_b, rag_payload["citation_map"])
    assert "[S2]" in val_b["valid_citations"]
    assert len(val_b["invalid_citations"]) == 0

    # Unsupported query (zero context)
    empty_payload = build_rag_context([])
    assert empty_payload["has_context"] is False
    assert empty_payload["sources"] == []
    assert empty_payload["citation_map"] == {}
    assert "couldn't find" in empty_payload["fallback_answer"] and "indexed documents" in empty_payload["fallback_answer"]
    print("Citation correctness and unsupported query fallback verified.")


async def test_api_chat_citations():
    print("\n--- 7. Testing End-to-End Chat API Response with Citations ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        test_user = f"cite_user_{uuid.uuid4().hex[:6]}"
        password = "strongpassword123"

        reg_res = await client.post("/api/auth/register", json={"user_id": test_user, "password": password})
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Unsupported query before ingestion -> fallback answer & empty sources
        res_empty = await client.post("/api/chat/", json={"query": "Explain string theory in detail."}, headers=headers)
        assert res_empty.status_code == 200
        empty_body = res_empty.json()
        assert "couldn't find" in empty_body["answer"] and "indexed documents" in empty_body["answer"]
        assert empty_body["sources"] == []

        # 2. Upload sample document
        pdf_bytes = make_test_pdf("The Transformer encoder uses self-attention followed by feed-forward layers.")
        upload_res = await client.post(
            "/api/documents/upload",
            files={"file": ("attention.pdf", pdf_bytes, "application/pdf")},
            headers=headers
        )
        doc_id = upload_res.json()["document_id"]

        # Wait for document to be indexed
        for _ in range(15):
            st = (await client.get(f"/api/documents/{doc_id}", headers=headers)).json()
            if st["status"] == "indexed":
                break
            await asyncio.sleep(0.5)

        # 3. Query chat endpoint
        chat_res = await client.post("/api/chat/", json={"query": "How does the Transformer encoder work?"}, headers=headers)
        assert chat_res.status_code == 200
        chat_body = chat_res.json()
        assert "answer" in chat_body
        assert "sources" in chat_body
        assert "citation_map" in chat_body
        assert "document_sources" in chat_body
        assert len(chat_body["sources"]) > 0
        first_source = chat_body["sources"][0]
        assert "id" in first_source
        assert first_source["id"] == "S1"
        assert first_source["filename"] == "attention.pdf"
        assert "chunk_index" in first_source
        assert "score" in first_source
        print("End-to-End Chat API source citation verified.")


def main():
    test_schema_contract()
    test_stable_identifier_generation()
    test_citation_map_construction()
    test_citation_validation()
    test_source_deduplication_and_grouping()
    test_citation_correctness_and_unsupported_questions()
    asyncio.run(test_api_chat_citations())
    print("\n[Success] Day 142 RAG Source Citations Verified Successfully!")


if __name__ == "__main__":
    main()
