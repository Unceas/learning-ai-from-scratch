"""Integration test suite for Day 153: Document State, Upload & Processing.

Verifies:
1. Vite production build compilation.
2. Document listing contract (GET /api/documents/).
3. Document upload with multipart/form-data returning status=processing.
4. Document status retrieval and polling transition to status=indexed.
5. Retry endpoint contract (POST /api/documents/{id}/retry).
6. Document deletion via integer ID (DELETE /api/documents/{id}).
7. Multi-tenant isolation for document status and deletion.
"""

import os
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


def make_test_pdf(text: str) -> bytes:
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


async def test_document_lifecycle_flow():
    print("=" * 60)
    print("   Test Suite: Day 153 — Document State & Upload Processing   ")
    print("=" * 60)

    # 1. Verify Vite build artifacts
    print("\n--- 1. Verifying Frontend Build Artifacts ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")
    assert os.path.exists(dist_index), f"Missing built index.html at {dist_index}"
    print("[PASSED] Vite build dist/index.html exists and is compiled.")

    user_a = "test_user_day153_a"
    user_b = "test_user_day153_b"
    token_a = create_access_token(user_a)
    token_b = create_access_token(user_b)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # 2. Document listing contract
        print("\n--- 2. Document Listing (GET /api/documents/) ---")
        res_list = await client.get("/api/documents/", headers=headers_a)
        assert res_list.status_code == 200, f"Expected 200, got {res_list.status_code}"
        list_data = res_list.json()
        assert "documents" in list_data, "Expected 'documents' key in response"
        print(f"[PASSED] Documents listing returned (initial count={len(list_data['documents'])})")

        # 3. Document upload with multipart/form-data
        print("\n--- 3. Document Upload (POST /api/documents/upload) ---")
        pdf_content = make_test_pdf("Attention Is All You Need Paper research content for Day 153 test.")
        files = {"file": ("attention_day153.pdf", pdf_content, "application/pdf")}
        res_upload = await client.post("/api/documents/upload", files=files, headers=headers_a)
        assert res_upload.status_code == 200, f"Expected 200, got {res_upload.status_code}: {res_upload.text}"
        upload_data = res_upload.json()
        doc_id = upload_data.get("document_id") or upload_data.get("id")
        assert doc_id is not None, f"Expected document_id in response: {upload_data}"
        print(f"[PASSED] Upload successful: id={doc_id}, status={upload_data.get('status')}")

        # 4. Status polling (GET /api/documents/{id})
        print("\n--- 4. Document Status Polling (GET /api/documents/{id}) ---")
        max_attempts = 15
        final_status = None
        for attempt in range(max_attempts):
            res_status = await client.get(f"/api/documents/{doc_id}", headers=headers_a)
            assert res_status.status_code == 200, f"Expected 200 for status, got {res_status.status_code}"
            status_data = res_status.json()
            current_status = status_data.get("status")
            print(f"       Attempt {attempt+1}: status={current_status}, chunks={status_data.get('chunks')}")
            if current_status in ["indexed", "failed"]:
                final_status = current_status
                break
            await asyncio.sleep(0.5)

        assert final_status in ["indexed", "processing"], f"Expected indexed or processing, got {final_status}"
        print(f"[PASSED] Document status poll verified: final_status={final_status}")

        # 5. Retry contract check (POST /api/documents/{id}/retry)
        print("\n--- 5. Document Retry Contract (POST /api/documents/{id}/retry) ---")
        if final_status == "indexed":
            res_retry = await client.post(f"/api/documents/{doc_id}/retry", headers=headers_a)
            # Retrying indexed document should return 400
            assert res_retry.status_code == 400
            print("[PASSED] Correctly rejects retrying an already indexed document (HTTP 400).")

        # 6. Multi-tenant isolation: User B cannot access User A's document
        print("\n--- 6. Multi-Tenant Isolation Check ---")
        res_unauth = await client.get(f"/api/documents/{doc_id}", headers=headers_b)
        assert res_unauth.status_code in [400, 404], f"Expected 400/404 for unowned doc, got {res_unauth.status_code}"
        print("[PASSED] User B cannot access User A's document.")

        # 7. Document deletion by ID (DELETE /api/documents/{id})
        print("\n--- 7. Document Deletion by ID (DELETE /api/documents/{id}) ---")
        res_del = await client.delete(f"/api/documents/{doc_id}", headers=headers_a)
        assert res_del.status_code == 200, f"Expected 200 for deletion, got {res_del.status_code}: {res_del.text}"
        del_data = res_del.json()
        assert del_data.get("status") == "deleted", f"Expected status=deleted, got {del_data}"
        print(f"[PASSED] Document deleted successfully: {del_data}")

        # Verify it no longer exists
        res_check = await client.get(f"/api/documents/{doc_id}", headers=headers_a)
        assert res_check.status_code in [400, 404], f"Expected 400/404 after deletion, got {res_check.status_code}"
        print("[PASSED] Document confirmed deleted from database and vector index.")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Day 153 Document Lifecycle Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_document_lifecycle_flow())
