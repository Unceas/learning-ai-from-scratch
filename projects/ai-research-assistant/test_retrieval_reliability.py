import asyncio
from pathlib import Path
import uuid
import httpx

from backend.main import app
from backend.database import SessionLocal
from backend.models import Document
from backend.services.document_processor import process_document_background
from backend.services.vector_store import VectorStore
from retrieval import retrieve, get_indexed_document_ids, db_retrieve


def make_test_pdf(text: str = "Test document content for retrieval.") -> bytes:
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
        user_a = f"ret_user_a_{unique_suffix}"
        user_b = f"ret_user_b_{unique_suffix}"
        user_c_empty = f"ret_user_c_{unique_suffix}"
        password = "strongpassword123"

        token_a = await get_test_token(client, user_a, password)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = await get_test_token(client, user_b, password)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        token_c = await get_test_token(client, user_c_empty, password)

        db = SessionLocal()
        try:
            # -------------------------------------------------------------
            # Test 1: Empty document set returns cleanly
            # -------------------------------------------------------------
            print("--- 1. Testing Empty Document Set ---")
            indexed_ids_c = get_indexed_document_ids(db, user_c_empty)
            assert indexed_ids_c == []
            empty_results = retrieve(db, user_c_empty, "Any query here", top_k=5)
            print("Empty user retrieval result:", empty_results)
            assert empty_results == [], "Expected empty list when user has no indexed documents"

            # -------------------------------------------------------------
            # Setup Documents for User A & User B
            # -------------------------------------------------------------
            print("\n--- 2. Setting Up Documents for User A and User B ---")
            # User A - Document 1 (Indexed: Quantum Computing)
            pdf_quantum = make_test_pdf("Quantum computing uses qubits and quantum superposition principles.")
            res_a1 = await client.post("/api/documents/upload", files={"file": ("quantum.pdf", pdf_quantum, "application/pdf")}, headers=headers_a)
            doc_id_a1 = res_a1.json()["document_id"]

            # User A - Document 2 (Failed / Processing simulation)
            pdf_failed = make_test_pdf("This document will be marked as failed.")
            res_a2 = await client.post("/api/documents/upload", files={"file": ("failed_doc.pdf", pdf_failed, "application/pdf")}, headers=headers_a)
            doc_id_a2 = res_a2.json()["document_id"]

            # User A - Document 3 (Processing simulation)
            pdf_proc = make_test_pdf("This document will stay in processing state.")
            res_a3 = await client.post("/api/documents/upload", files={"file": ("processing_doc.pdf", pdf_proc, "application/pdf")}, headers=headers_a)
            doc_id_a3 = res_a3.json()["document_id"]

            # User B - Document 1 (Indexed: Secret Artificial Intelligence Paper)
            pdf_secret = make_test_pdf("Confidential User B Artificial Intelligence deep learning research findings.")
            res_b1 = await client.post("/api/documents/upload", files={"file": ("user_b_ai.pdf", pdf_secret, "application/pdf")}, headers=headers_b)
            doc_id_b1 = res_b1.json()["document_id"]

            # Wait for User A doc 1 and User B doc 1 to index
            for _ in range(15):
                st_a = (await client.get(f"/api/documents/{doc_id_a1}", headers=headers_a)).json()
                st_b = (await client.get(f"/api/documents/{doc_id_b1}", headers=headers_b)).json()
                if st_a["status"] == "indexed" and st_b["status"] == "indexed":
                    break
                await asyncio.sleep(0.5)

            # Explicitly set doc_id_a2 to failed in SQLite
            doc_a2_record = db.query(Document).filter(Document.id == doc_id_a2).first()
            if doc_a2_record:
                doc_a2_record.status = "failed"
                doc_a2_record.error_message = "Simulated manual failure for test"
                db.commit()

            # Explicitly set doc_id_a3 to processing in SQLite
            doc_a3_record = db.query(Document).filter(Document.id == doc_id_a3).first()
            if doc_a3_record:
                doc_a3_record.status = "processing"
                db.commit()

            # -------------------------------------------------------------
            # Test 2: get_indexed_document_ids filters only indexed documents
            # -------------------------------------------------------------
            print("\n--- 3. Verifying Authoritative SQLite Document Eligibility ---")
            indexed_ids_a = get_indexed_document_ids(db, user_a)
            print("User A Indexed Document IDs:", indexed_ids_a)
            assert doc_id_a1 in indexed_ids_a
            assert doc_id_a2 not in indexed_ids_a, "Failed document must NOT be in indexed_ids"
            assert doc_id_a3 not in indexed_ids_a, "Processing document must NOT be in indexed_ids"
            assert doc_id_b1 not in indexed_ids_a, "User B document must NOT belong to User A"

            indexed_ids_b = get_indexed_document_ids(db, user_b)
            print("User B Indexed Document IDs:", indexed_ids_b)
            assert doc_id_b1 in indexed_ids_b
            assert doc_id_a1 not in indexed_ids_b

            # -------------------------------------------------------------
            # Test 3: Processing-state isolation (Only indexed docs retrieved)
            # -------------------------------------------------------------
            print("\n--- 4. Testing Processing-State Isolation ---")
            results_a = retrieve(db, user_a, "quantum qubits and computing", top_k=5)
            print(f"Retrieved {len(results_a)} chunks for User A")
            assert len(results_a) > 0

            for r in results_a:
                assert r["document_id"] == doc_id_a1
                assert r["filename"] == "quantum.pdf"
                # Validate metadata schema
                assert "text" in r
                assert "score" in r
                assert "document_id" in r
                assert "filename" in r
                assert "chunk_index" in r
                print("Sample Retrieved Chunk:", r)

            # Querying for text that was in the failed or processing document
            results_failed = retrieve(db, user_a, "marked as failed", top_k=5)
            # Must NOT contain doc_id_a2
            failed_matches = [r for r in results_failed if r["document_id"] == doc_id_a2]
            assert len(failed_matches) == 0, "Failed document chunks must never appear in retrieval"

            results_proc = retrieve(db, user_a, "stay in processing state", top_k=5)
            # Must NOT contain doc_id_a3
            proc_matches = [r for r in results_proc if r["document_id"] == doc_id_a3]
            assert len(proc_matches) == 0, "Processing document chunks must never appear in retrieval"

            # -------------------------------------------------------------
            # Test 4: Cross-user isolation in ChromaDB
            # -------------------------------------------------------------
            print("\n--- 5. Testing Multi-User Vector Isolation ---")
            # User A queries for content present in User B's document
            cross_results_a = retrieve(db, user_a, "Confidential User B Artificial Intelligence", top_k=5)
            user_b_in_a = [r for r in cross_results_a if r["document_id"] == doc_id_b1 or r["filename"] == "user_b_ai.pdf"]
            assert len(user_b_in_a) == 0, "User B documents must NEVER appear in User A retrieval"

            # User B querying for User B's content gets it
            results_b = retrieve(db, user_b, "Confidential Artificial Intelligence research", top_k=5)
            assert len(results_b) > 0
            assert results_b[0]["document_id"] == doc_id_b1
            assert results_b[0]["filename"] == "user_b_ai.pdf"
            print("User B successfully retrieved own document:", results_b[0]["filename"])

            # -------------------------------------------------------------
            # Test 5: Backward compatibility with keyword TF-IDF retrieve
            # -------------------------------------------------------------
            print("\n--- 6. Testing Backward-Compatible TF-IDF retrieve ---")
            tfidf_res = retrieve("machine learning", ["machine learning is great", "cooking recipe"])
            assert len(tfidf_res) > 0
            assert "machine learning is great" in tfidf_res[0][1]
            print("Keyword TF-IDF fallback passed successfully.")

        finally:
            db.close()

    print("\n[Success] Day 140 Retrieval Reliability & Document-Level Filtering Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
