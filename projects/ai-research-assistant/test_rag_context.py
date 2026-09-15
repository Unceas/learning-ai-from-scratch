"""Test suite for Day 141: RAG Context Builder and Source Attribution."""

import asyncio
import uuid
import httpx

from backend.main import app
from backend.services.rag_context import (
    RetrievedChunk,
    normalize_chunk,
    build_context,
    build_rag_context,
    MAX_CONTEXT_CHUNKS
)
from backend.services.rag_service import run_rag_pipeline
from llm import generate_answer
from test_retrieval_reliability import make_test_pdf


def test_chunk_normalization():
    print("--- 1. Testing RetrievedChunk Normalization ---")
    chunk_obj = RetrievedChunk(
        text="Sample chunk content",
        score=0.95,
        document_id=1,
        filename="report.pdf",
        chunk_index=2,
        page=1
    )
    assert normalize_chunk(chunk_obj) == chunk_obj

    dict_chunk = {
        "text": "Dict chunk content",
        "score": 0.88,
        "document_id": 42,
        "document": "quarterly.pdf",
        "chunk_id": 3,
        "page": 2
    }
    norm = normalize_chunk(dict_chunk)
    assert norm.text == "Dict chunk content"
    assert norm.score == 0.88
    assert norm.document_id == 42
    assert norm.filename == "quarterly.pdf"
    assert norm.chunk_index == 3
    assert norm.page == 2
    print("RetrievedChunk normalization passed.")


def test_context_formatting():
    print("\n--- 2. Testing Context Builder String Formatting ---")
    chunks = [
        RetrievedChunk(text="Chunk 1 body", score=0.9, document_id=10, filename="doc1.pdf", chunk_index=0),
        RetrievedChunk(text="Chunk 2 body", score=0.8, document_id=10, filename="doc1.pdf", chunk_index=1),
    ]
    formatted = build_context(chunks)
    assert "SOURCE 1" in formatted
    assert "File: doc1.pdf" in formatted
    assert "Document ID: 10" in formatted
    assert "Chunk: 0" in formatted
    assert "Chunk 1 body" in formatted

    assert "SOURCE 2" in formatted
    assert "Chunk: 1" in formatted
    assert "Chunk 2 body" in formatted
    print("Context formatting passed.")


def test_context_chunk_limiting():
    print("\n--- 3. Testing Context Chunk Limit Enforcing ---")
    many_chunks = [
        {"text": f"Chunk {i} text", "score": 0.5, "document_id": i, "filename": f"doc_{i}.pdf", "chunk_index": 0}
        for i in range(15)
    ]
    result = build_rag_context(many_chunks)
    assert len(result["sources"]) == MAX_CONTEXT_CHUNKS
    assert len(result["document_sources"]) == MAX_CONTEXT_CHUNKS
    assert f"SOURCE {MAX_CONTEXT_CHUNKS}" in result["context"]
    assert f"SOURCE {MAX_CONTEXT_CHUNKS + 1}" not in result["context"]
    print(f"Context chunk limiting passed (max: {MAX_CONTEXT_CHUNKS}).")


def test_source_attribution_and_deduplication():
    print("\n--- 4. Testing Source Attribution & Document Deduplication ---")
    chunks = [
        {"text": "Text A", "score": 0.95, "document_id": 1, "filename": "doc_alpha.pdf", "chunk_index": 0, "page": 1},
        {"text": "Text B", "score": 0.85, "document_id": 1, "filename": "doc_alpha.pdf", "chunk_index": 1, "page": 2},
        {"text": "Text C", "score": 0.75, "document_id": 2, "filename": "doc_beta.pdf", "chunk_index": 0, "page": 1},
        {"text": "Text D", "score": 0.65, "document_id": 2, "filename": "doc_beta.pdf", "chunk_index": 1, "page": 2},
    ]
    result = build_rag_context(chunks)
    assert len(result["sources"]) == 4
    # Detailed chunk sources contain exact chunk pointers
    assert result["sources"][0]["chunk_index"] == 0
    assert result["sources"][1]["chunk_index"] == 1

    # Document sources must be deduplicated
    assert len(result["document_sources"]) == 2
    doc_ids = [d["document_id"] for d in result["document_sources"]]
    assert doc_ids == [1, 2]
    print("Source separation and document deduplication passed.")


def test_zero_chunk_fallback():
    print("\n--- 5. Testing Zero-Chunk Fallback ---")
    empty_result = build_rag_context([])
    assert empty_result["has_context"] is False
    assert empty_result["context"] == ""
    assert empty_result["sources"] == []
    assert empty_result["document_sources"] == []
    assert empty_result["fallback_answer"] == "I couldn't find relevant information in the indexed documents."

    # Verify generate_answer yields fallback without calling LLM
    stream = generate_answer("Any query without context", results=[])
    tokens = list(stream)
    assert "".join(tokens) == "I couldn't find relevant information in the indexed documents."
    print("Zero-chunk fallback passed.")


async def test_api_integration():
    print("\n--- 6. Testing End-to-End Chat API with Structured Sources ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unique_user = f"rag_user_{uuid.uuid4().hex[:6]}"
        password = "strongpassword123"

        reg_res = await client.post("/api/auth/register", json={"user_id": unique_user, "password": password})
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Query before uploading documents -> zero context fallback
        res_empty_chat = await client.post("/api/chat/", json={"query": "Tell me about quantum physics"}, headers=headers)
        assert res_empty_chat.status_code == 200
        empty_data = res_empty_chat.json()
        assert empty_data["answer"] == "I couldn't find relevant information in the indexed documents."
        assert empty_data["sources"] == []
        assert empty_data["document_sources"] == []

        # Upload document
        pdf_bytes = make_test_pdf("Superconducting qubits operate at millikelvin temperatures.")
        res_upload = await client.post(
            "/api/documents/upload",
            files={"file": ("qubits.pdf", pdf_bytes, "application/pdf")},
            headers=headers
        )
        doc_id = res_upload.json()["document_id"]

        # Wait for indexing
        for _ in range(15):
            st = (await client.get(f"/api/documents/{doc_id}", headers=headers)).json()
            if st["status"] == "indexed":
                break
            await asyncio.sleep(0.5)

        # Query after indexing
        res_chat = await client.post("/api/chat/", json={"query": "What temperature do superconducting qubits operate at?"}, headers=headers)
        assert res_chat.status_code == 200
        chat_data = res_chat.json()
        assert "answer" in chat_data
        assert "sources" in chat_data
        assert "document_sources" in chat_data
        assert len(chat_data["sources"]) > 0
        assert len(chat_data["document_sources"]) > 0
        assert chat_data["document_sources"][0]["filename"] == "qubits.pdf"
        assert chat_data["sources"][0]["filename"] == "qubits.pdf"
        assert "chunk_index" in chat_data["sources"][0]
        print("End-to-End Chat API source attribution passed.")


def main():
    test_chunk_normalization()
    test_context_formatting()
    test_context_chunk_limiting()
    test_source_attribution_and_deduplication()
    test_zero_chunk_fallback()
    asyncio.run(test_api_integration())
    print("\n[Success] Day 141 RAG Context Builder & Source Attribution Verified Successfully!")


if __name__ == "__main__":
    main()
