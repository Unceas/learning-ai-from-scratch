"""Day 139 -- Document Processing Reliability Test Suite.

Verifies:
Test 1 -- Normal processing (upload -> processing -> indexed)
Test 2 -- Duplicate execution (run processor twice -> same vector count, no duplicates)
Test 3 -- Failure (forced exception -> status=failed, error_message!=null, no vectors remain)
Test 4 -- Retry (failed -> retry -> processing -> indexed)
Test 5 -- User isolation (User B attempts to retry User A's document -> 404)
Test 6 -- Changed chunk count (5 chunks -> 3 chunks -> exactly 3 vectors, not 5)
Test 7 -- Partial indexing failure (failure halfway -> status=failed, 0 vectors in ChromaDB)
"""

import asyncio
import uuid
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.vector_store import VectorStore
from backend.services.document_processor import process_document_background
from backend.database import SessionLocal
from backend.models import Document


def make_test_pdf(text: str = "Test document content for reliability.") -> bytes:
    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length {len(text) + 20} >> stream
BT
/F1 12 Tf
100 700 Td
({text}) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
{350 + len(text)}
%%EOF
"""
    return pdf.encode("latin1")


async def get_test_token(client: httpx.AsyncClient, user_id: str, password: str) -> str:
    res = await client.post("/api/auth/register", json={
        "user_id": user_id,
        "password": password
    })
    if res.status_code == 200:
        return res.json()["access_token"]
    login_res = await client.post("/api/auth/login", json={
        "user_id": user_id,
        "password": password
    })
    return login_res.json()["access_token"]


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:6]
        user_a = f"rel_user_a_{unique_suffix}"
        user_b = f"rel_user_b_{unique_suffix}"
        password = "strongpassword123"

        print(f"=== Registering Users ({user_a}, {user_b}) ===")
        token_a = await get_test_token(client, user_a, password)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = await get_test_token(client, user_b, password)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        vector_store = VectorStore()

        # -------------------------------------------------------------
        # Test 1 -- Normal processing (upload -> processing -> indexed)
        # -------------------------------------------------------------
        print("\n--- Test 1: Normal processing (upload -> processing -> indexed) ---")
        pdf_bytes = make_test_pdf("Reliability test document content for normal processing.")
        files = {"file": ("doc_normal.pdf", pdf_bytes, "application/pdf")}

        res_upload = await client.post("/api/documents/upload", files=files, headers=headers_a)
        assert res_upload.status_code == 200, f"Upload failed: {res_upload.text}"
        doc_data = res_upload.json()
        doc_id = doc_data["document_id"]
        assert doc_id is not None
        assert doc_data["status"] == "processing"

        # Poll until indexed
        status_data = None
        for _ in range(15):
            res_status = await client.get(f"/api/documents/{doc_id}", headers=headers_a)
            status_data = res_status.json()
            if status_data["status"] == "indexed":
                break
            await asyncio.sleep(0.3)

        print("Test 1 Status Data:", status_data)
        assert status_data["status"] == "indexed"
        assert status_data["chunks"] >= 1
        assert status_data["error_message"] is None
        assert status_data["processing_attempts"] >= 1

        vec_count = vector_store.count_by_document_id(doc_id)
        print(f"Test 1 Vector Count: {vec_count}")
        assert vec_count == status_data["chunks"]
        print("[PASSED] Test 1: Normal processing verified")

        # -------------------------------------------------------------
        # Test 2 -- Duplicate execution (idempotency, same vector count)
        # -------------------------------------------------------------
        print("\n--- Test 2: Duplicate execution ---")
        initial_vec_count = vector_store.count_by_document_id(doc_id)

        # Run background processor again on the exact same document
        process_document_background(doc_id)

        res_status_after_dup = await client.get(f"/api/documents/{doc_id}", headers=headers_a)
        dup_data = res_status_after_dup.json()
        print("Test 2 Status After Duplicate Run:", dup_data)
        assert dup_data["status"] == "indexed"
        assert dup_data["processing_attempts"] == 2

        new_vec_count = vector_store.count_by_document_id(doc_id)
        print(f"Test 2 Vector Count: initial={initial_vec_count}, after duplicate={new_vec_count}")
        assert new_vec_count == initial_vec_count, "Duplicate execution must not duplicate vectors!"

        # Verify vector IDs are deterministic (e.g., f"{doc_id}:{i}")
        doc_vectors = vector_store.get_by_document_id(doc_id)
        for expected_i in range(new_vec_count):
            assert f"{doc_id}:{expected_i}" in doc_vectors["ids"]
        print("[PASSED] Test 2: Duplicate execution creates no duplicate vectors")

        # -------------------------------------------------------------
        # Test 3 -- Failure (force exception -> failed, error!=null, 0 vectors)
        # -------------------------------------------------------------
        print("\n--- Test 3: Failure handling and partial vector cleanup ---")
        fail_pdf = make_test_pdf("Content destined to fail during indexing.")
        files_fail = {"file": ("doc_fail.pdf", fail_pdf, "application/pdf")}

        with patch("backend.services.document_processor.process_document", side_effect=ValueError("Simulated PDF parsing crash")):
            res_fail_upload = await client.post("/api/documents/upload", files=files_fail, headers=headers_a)
            assert res_fail_upload.status_code == 200
            fail_doc_id = res_fail_upload.json()["document_id"]

            # Wait for background task to catch error and update SQLite
            fail_status = None
            for _ in range(15):
                res_fail_status = await client.get(f"/api/documents/{fail_doc_id}", headers=headers_a)
                fail_status = res_fail_status.json()
                if fail_status["status"] == "failed":
                    break
                await asyncio.sleep(0.3)

        print("Test 3 Failed Status Data:", fail_status)
        assert fail_status["status"] == "failed"
        assert fail_status["error_message"] == "Simulated PDF parsing crash"
        fail_vec_count = vector_store.count_by_document_id(fail_doc_id)
        print(f"Test 3 Vector Count for Failed Document: {fail_vec_count}")
        assert fail_vec_count == 0, "Failed document must leave 0 vectors in ChromaDB"
        print("[PASSED] Test 3: Failure cleans up vectors and records error")

        # -------------------------------------------------------------
        # Test 4 -- Retry (failed -> retry -> processing -> indexed)
        # -------------------------------------------------------------
        print("\n--- Test 4: Retry failed document ---")
        # Now retry the failed document without the forced error
        res_retry = await client.post(f"/api/documents/{fail_doc_id}/retry", headers=headers_a)
        print("Retry Response Status:", res_retry.status_code)
        print("Retry Response Data:", res_retry.json())
        assert res_retry.status_code == 200
        assert res_retry.json()["status"] == "processing"
        assert res_retry.json()["error_message"] is None

        # Wait for retry to finish indexing
        retry_status = None
        for _ in range(15):
            res_retry_status = await client.get(f"/api/documents/{fail_doc_id}", headers=headers_a)
            retry_status = res_retry_status.json()
            if retry_status["status"] == "indexed":
                break
            await asyncio.sleep(0.3)

        print("Test 4 Post-Retry Status Data:", retry_status)
        assert retry_status["status"] == "indexed"
        assert retry_status["error_message"] is None
        assert retry_status["processing_attempts"] >= 2
        retry_vec_count = vector_store.count_by_document_id(fail_doc_id)
        assert retry_vec_count >= 1
        print("[PASSED] Test 4: Retry successfully transitions failed -> processing -> indexed")

        # -------------------------------------------------------------
        # Test 5 -- User isolation (User B cannot retry User A's document)
        # -------------------------------------------------------------
        print("\n--- Test 5: User isolation on retry ---")
        # Mark fail_doc_id back to failed in DB for test
        db = SessionLocal()
        try:
            doc_record = db.query(Document).filter(Document.id == fail_doc_id).first()
            doc_record.status = "failed"
            doc_record.error_message = "Temporary failure for isolation test"
            db.commit()
        finally:
            db.close()

        # User B attempts to retry User A's document
        res_b_retry = await client.post(f"/api/documents/{fail_doc_id}/retry", headers=headers_b)
        print("User B Retry Status Code:", res_b_retry.status_code)
        print("User B Retry Response Body:", res_b_retry.json())
        assert res_b_retry.status_code == 404, "User B must receive 404 when retrying User A's document"
        print("[PASSED] Test 5: User isolation on retry enforced (404)")

        # -------------------------------------------------------------
        # Test 6 -- Changed chunk count (5 chunks -> 3 chunks -> exactly 3 vectors)
        # -------------------------------------------------------------
        print("\n--- Test 6: Changed chunk count purge ---")
        # Reindex fail_doc_id with 5 simulated chunks
        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[{"page": 1, "text": "Dummy page"}]), \
             patch("backend.services.document_service.chunk_text", return_value=[f"Chunk {i}" for i in range(5)]):
            process_document_background(fail_doc_id)

        vecs_5 = vector_store.count_by_document_id(fail_doc_id)
        print(f"Chunk count after 5-chunk indexing: {vecs_5}")
        assert vecs_5 == 5

        # Now re-process with 3 chunks
        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[{"page": 1, "text": "Dummy page"}]), \
             patch("backend.services.document_service.chunk_text", return_value=[f"Chunk {i}" for i in range(3)]):
            process_document_background(fail_doc_id)

        vecs_3 = vector_store.count_by_document_id(fail_doc_id)
        print(f"Chunk count after 3-chunk re-indexing: {vecs_3}")
        assert vecs_3 == 3, f"Expected exactly 3 vectors, found {vecs_3} (stale vectors were not cleaned up)"

        # Verify exact IDs remaining
        vec_data_3 = vector_store.get_by_document_id(fail_doc_id)
        expected_ids = {f"{fail_doc_id}:0", f"{fail_doc_id}:1", f"{fail_doc_id}:2"}
        assert set(vec_data_3["ids"]) == expected_ids
        print("[PASSED] Test 6: Stale chunks purged on re-indexing with fewer chunks")

        # -------------------------------------------------------------
        # Test 7 -- Partial indexing failure
        # -------------------------------------------------------------
        print("\n--- Test 7: Partial indexing failure cleans up vectors ---")
        # Create a new document for this test
        partial_pdf = make_test_pdf("Content for partial indexing failure test.")
        files_partial = {"file": ("doc_partial.pdf", partial_pdf, "application/pdf")}
        res_part = await client.post("/api/documents/upload", files=files_partial, headers=headers_a)
        assert res_part.status_code == 200
        part_doc_id = res_part.json()["document_id"]

        # Simulate partial indexing: insert some vectors first, then fail
        vector_store.upsert_documents(
            texts=["Partial chunk 1", "Partial chunk 2"],
            embeddings=[[0.1] * 384, [0.2] * 384],
            metadatas=[
                {"user_id": user_a, "document_id": part_doc_id, "chunk_index": 0},
                {"user_id": user_a, "document_id": part_doc_id, "chunk_index": 1}
            ],
            ids=[f"{part_doc_id}:0", f"{part_doc_id}:1"]
        )
        assert vector_store.count_by_document_id(part_doc_id) == 2

        # Now trigger background processing with an error midway
        with patch("backend.services.document_processor.process_document", side_effect=RuntimeError("Midway indexing connection lost")):
            process_document_background(part_doc_id)

        # Verify SQLite is failed and ChromaDB has 0 vectors
        db = SessionLocal()
        try:
            part_doc = db.query(Document).filter(Document.id == part_doc_id).first()
            print("Partial Failure Doc Status:", part_doc.status, "| Error:", part_doc.error_message)
            assert part_doc.status == "failed"
            assert "Midway indexing connection lost" in part_doc.error_message
        finally:
            db.close()

        part_vecs = vector_store.count_by_document_id(part_doc_id)
        print(f"Partial Failure ChromaDB Vector Count: {part_vecs}")
        assert part_vecs == 0, "Partial vectors must be completely cleaned up on failure"
        print("[PASSED] Test 7: Partial indexing failure cleanly rolled back ChromaDB vectors")

    print("\n" + "=" * 60)
    print("ALL 7 DAY 139 RELIABILITY TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
