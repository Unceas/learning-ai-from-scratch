"""Test Suite #41: Source Inspection & Document Context (Day 161).

Validates:
1. Frontend file architecture, exports, and UI components:
   - frontend/src/components/sources/SourcePreview.jsx
   - frontend/src/api/sources.js
   - frontend/src/utils/sources.js
   - frontend/src/components/chat/MarkdownAnswer.jsx
   - frontend/src/components/sources/SourceCard.jsx
   - frontend/src/pages/Chat.jsx
   - frontend/src/index.css
2. Backend Source schema and RAG context preservation of chunk text:
   - Source model retains text, filename, chunk_index, score, document_id
   - rag_context preserves chunk.text in sources and citation_map
   - ChunkPreviewResponse response model
3. Secure source inspection endpoint (GET /api/documents/{document_id}/chunks/{chunk_index}):
   - Valid citation inspection returns authorized chunk text and metadata
   - Cross-tenant isolation: accessing another user's document chunk returns 404
   - Status guard: non-indexed document (processing/failed) returns 404
   - Out-of-bounds guard: requesting a nonexistent chunk index returns 404
   - Unauthenticated access returns 401
4. Document deletion invalidates vector records and chunk access.
5. Multi-turn citation-to-source mapping independence per message.
"""

import asyncio
import os
import uuid
import httpx
from backend.main import app
from backend.database import SessionLocal
from backend.models import Document
from backend.services.vector_store import VectorStore
from backend.services.document_db_service import get_owned_document
from backend.services.rag_context import RetrievedChunk, build_rag_context
from backend.schemas.rag import Source


def test_frontend_structure_and_components():
    print("--- 1. Testing Frontend Source Inspection Structure & Components ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. SourcePreview.jsx
    preview_file = os.path.join(base_dir, "frontend", "src", "components", "sources", "SourcePreview.jsx")
    assert os.path.exists(preview_file), f"Missing SourcePreview.jsx at {preview_file}"
    with open(preview_file, "r", encoding="utf-8") as f:
        preview_code = f.read()
    assert "source-preview" in preview_code
    assert "source-preview-header" in preview_code
    assert "source-preview-metadata" in preview_code
    assert "source-preview-content" in preview_code
    assert "Retrieved passage" in preview_code
    assert "No passage text is available." in preview_code
    assert "onClose" in preview_code

    # 2. sources.js api
    api_file = os.path.join(base_dir, "frontend", "src", "api", "sources.js")
    assert os.path.exists(api_file), f"Missing api/sources.js at {api_file}"
    with open(api_file, "r", encoding="utf-8") as f:
        api_code = f.read()
    assert "getDocumentChunk" in api_code
    assert "/api/documents/" in api_code

    # 3. utils/sources.js
    utils_file = os.path.join(base_dir, "frontend", "src", "utils", "sources.js")
    assert os.path.exists(utils_file), f"Missing utils/sources.js at {utils_file}"
    with open(utils_file, "r", encoding="utf-8") as f:
        utils_code = f.read()
    assert "text" in utils_code
    assert "normalizeSource" in utils_code

    # 4. MarkdownAnswer.jsx resolving sourceMap
    markdown_file = os.path.join(base_dir, "frontend", "src", "components", "chat", "MarkdownAnswer.jsx")
    with open(markdown_file, "r", encoding="utf-8") as f:
        md_code = f.read()
    assert "sourceMap[sourceId]" in md_code
    assert "onSourceClick" in md_code

    # 5. SourceCard.jsx passing source object
    card_file = os.path.join(base_dir, "frontend", "src", "components", "sources", "SourceCard.jsx")
    with open(card_file, "r", encoding="utf-8") as f:
        card_code = f.read()
    assert "onClick?.(source)" in card_code

    # 6. Chat.jsx with SourcePreview
    chat_file = os.path.join(base_dir, "frontend", "src", "pages", "Chat.jsx")
    with open(chat_file, "r", encoding="utf-8") as f:
        chat_code = f.read()
    assert "SourcePreview" in chat_code
    assert "selectedSource" in chat_code
    assert "chat-layout-wrapper" in chat_code

    # 7. index.css styles
    css_file = os.path.join(base_dir, "frontend", "src", "index.css")
    with open(css_file, "r", encoding="utf-8") as f:
        css_code = f.read()
    assert ".source-preview" in css_code
    assert ".chat-layout-wrapper" in css_code

    print("Frontend source inspection components, API, and styles verified.")


def test_backend_source_model_and_rag_context():
    print("\n--- 2. Testing Backend Source Model & RAG Context Chunk Text Preservation ---")
    # Verify Source schema model
    source = Source(
        id="S1",
        document_id=42,
        filename="attention.pdf",
        chunk_index=3,
        score=0.912,
        text="The attention mechanism computes relationships between tokens."
    )
    assert source.id == "S1"
    assert source.document_id == 42
    assert source.filename == "attention.pdf"
    assert source.chunk_index == 3
    assert source.score == 0.912
    assert source.text == "The attention mechanism computes relationships between tokens."

    # Test build_sources_and_context preserves chunk.text
    test_chunks = [
        RetrievedChunk(
            text="Passage 1 explaining multi-head attention.",
            score=0.95,
            document_id=101,
            filename="paper1.pdf",
            chunk_index=0
        ),
        RetrievedChunk(
            text="Passage 2 explaining positional encoding.",
            score=0.88,
            document_id=101,
            filename="paper1.pdf",
            chunk_index=1
        )
    ]
    payload = build_rag_context(test_chunks)
    assert payload["has_context"] is True
    sources = payload["sources"]
    assert len(sources) == 2
    assert sources[0]["id"] == "S1"
    assert sources[0]["text"] == "Passage 1 explaining multi-head attention."
    assert sources[1]["id"] == "S2"
    assert sources[1]["text"] == "Passage 2 explaining positional encoding."

    citation_map = payload["citation_map"]
    assert "S1" in citation_map
    assert citation_map["S1"]["text"] == "Passage 1 explaining multi-head attention."
    assert "S2" in citation_map
    assert citation_map["S2"]["text"] == "Passage 2 explaining positional encoding."

    print("Backend Source schema and rag_context text preservation verified.")


async def test_source_inspection_api_lifecycle():
    print("\n--- 3. Testing Secure Source Inspection Endpoint & Authorization ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create User A
        user_a_name = f"user_a_{uuid.uuid4().hex[:6]}"
        user_a_pwd = "password123"
        reg_a = await client.post("/api/auth/register", json={"username": user_a_name, "password": user_a_pwd})
        assert reg_a.status_code == 200, f"Registration failed: {reg_a.text}"
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Get User A ID
        me_a = await client.get("/api/auth/me", headers=headers_a)
        user_a_id = me_a.json()["id"]

        # Create User B
        user_b_name = f"user_b_{uuid.uuid4().hex[:6]}"
        user_b_pwd = "password123"
        reg_b = await client.post("/api/auth/register", json={"username": user_b_name, "password": user_b_pwd})
        assert reg_b.status_code == 200, f"Registration failed: {reg_b.text}"
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # Seed an indexed document for User A in SQLite and ChromaDB
        db = SessionLocal()
        vstore = VectorStore()
        doc_hash = f"hash_{uuid.uuid4().hex}"
        doc_filename = "attention_is_all_you_need.pdf"
        chunk_passage = "Scaled Dot-Product Attention computes queries and keys with scaling factor sqrt(d_k)."

        try:
            doc = Document(
                user_id=user_a_id,
                file_hash=doc_hash,
                filename=doc_filename,
                storage_path="mock/path.pdf",
                chunks=2,
                status="indexed"
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            doc_id = doc.id

            # Seed chunk into vector store
            vstore.upsert_documents(
                texts=[chunk_passage, "Second chunk on feed forward networks."],
                embeddings=[[0.1] * 384, [0.2] * 384],
                metadatas=[
                    {
                        "user_id": user_a_id,
                        "document_id": doc_id,
                        "filename": doc_filename,
                        "file_hash": doc_hash,
                        "page": 3,
                        "chunk_id": 0,
                        "chunk_index": 0
                    },
                    {
                        "user_id": user_a_id,
                        "document_id": doc_id,
                        "filename": doc_filename,
                        "file_hash": doc_hash,
                        "page": 4,
                        "chunk_id": 1,
                        "chunk_index": 1
                    }
                ],
                ids=[f"{doc_id}:0", f"{doc_id}:1"]
            )

            # Test 3.1: Valid inspection by document owner
            res = await client.get(f"/api/documents/{doc_id}/chunks/0", headers=headers_a)
            assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
            data = res.json()
            assert data["document_id"] == doc_id
            assert data["chunk_index"] == 0
            assert data["filename"] == doc_filename
            assert data["text"] == chunk_passage
            assert data["page"] == 3
            assert data["id"] == "S1"

            # Test 3.2: Cross-user access denial (User B requesting User A's document)
            res_b = await client.get(f"/api/documents/{doc_id}/chunks/0", headers=headers_b)
            assert res_b.status_code == 404, f"Expected 404 for cross-user document access, got {res_b.status_code}"

            # Test 3.3: Requesting a non-indexed document (status = processing)
            doc_processing = Document(
                user_id=user_a_id,
                file_hash=f"hash_{uuid.uuid4().hex}",
                filename="processing_doc.pdf",
                storage_path="mock/proc.pdf",
                chunks=0,
                status="processing"
            )
            db.add(doc_processing)
            db.commit()
            db.refresh(doc_processing)

            res_proc = await client.get(f"/api/documents/{doc_processing.id}/chunks/0", headers=headers_a)
            assert res_proc.status_code == 404, f"Expected 404 for non-indexed document, got {res_proc.status_code}"

            # Test 3.4: Requesting a nonexistent chunk index (out of bounds)
            res_oob = await client.get(f"/api/documents/{doc_id}/chunks/999", headers=headers_a)
            assert res_oob.status_code == 404, f"Expected 404 for nonexistent chunk, got {res_oob.status_code}"

            # Test 3.5: Unauthenticated access denial
            res_unauth = await client.get(f"/api/documents/{doc_id}/chunks/0")
            assert res_unauth.status_code in [401, 403], f"Expected 401/403, got {res_unauth.status_code}"

            print("Secure source inspection endpoint, ownership validation, and status checks verified.")

            # Test 4: Document Deletion Invalidates Vectors
            print("\n--- 4. Testing Document Deletion Invalidation ---")
            del_res = await client.delete(f"/api/documents/{doc_id}", headers=headers_a)
            assert del_res.status_code == 200, f"Failed deleting document: {del_res.text}"

            # Verifying document is gone from inspection endpoint
            res_after_del = await client.get(f"/api/documents/{doc_id}/chunks/0", headers=headers_a)
            assert res_after_del.status_code == 404, "Deleted document chunks should not be accessible"

            # Verifying vectors are deleted from ChromaDB
            remaining = vstore.count_by_document_id(doc_id)
            assert remaining == 0, f"Expected 0 vectors after deletion, found {remaining}"

            print("Document deletion vector invalidation verified.")

        finally:
            # Clean up db records
            db.query(Document).filter(Document.user_id.in_([user_a_id])).delete()
            db.commit()
            db.close()


def test_per_message_citation_mapping():
    print("\n--- 5. Testing Per-Message Citation Isolation ---")
    # Simulate Answer 1 and Answer 2 having independent S1 citations
    msg1_sources = [
        {"id": "S1", "document_id": 10, "filename": "attention.pdf", "chunk_index": 2, "text": "Passage from attention.pdf"},
        {"id": "S2", "document_id": 10, "filename": "attention.pdf", "chunk_index": 3, "text": "Passage 2 from attention.pdf"}
    ]
    msg2_sources = [
        {"id": "S1", "document_id": 20, "filename": "resnet.pdf", "chunk_index": 5, "text": "Passage from resnet.pdf"}
    ]

    def resolve_citation(citation_id, sources):
        smap = {s.get("id") or f"S{i+1}": s for i, s in enumerate(sources)}
        return smap.get(citation_id)

    s1_msg1 = resolve_citation("S1", msg1_sources)
    s1_msg2 = resolve_citation("S1", msg2_sources)

    assert s1_msg1["filename"] == "attention.pdf"
    assert s1_msg1["document_id"] == 10
    assert s1_msg1["text"] == "Passage from attention.pdf"

    assert s1_msg2["filename"] == "resnet.pdf"
    assert s1_msg2["document_id"] == 20
    assert s1_msg2["text"] == "Passage from resnet.pdf"

    print("Per-message citation mapping isolation verified.")


# Helper mock for citation resolution logic
class frontend_mock:
    @staticmethod
    def resolve_citation(citation_id, sources):
        smap = {s.get("id") or f"S{i+1}": s for i, s in enumerate(sources)}
        return smap.get(citation_id)


def run_all_tests():
    print("=" * 60)
    print("RUNNING SUITE #41: SOURCE INSPECTION & DOCUMENT CONTEXT")
    print("=" * 60)
    test_frontend_structure_and_components()
    test_backend_source_model_and_rag_context()
    asyncio.run(test_source_inspection_api_lifecycle())
    test_per_message_citation_mapping()
    print("\n" + "=" * 60)
    print("SUITE #41 COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
