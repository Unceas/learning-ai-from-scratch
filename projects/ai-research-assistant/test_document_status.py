import asyncio
import uuid
import httpx
from backend.main import app


def make_test_pdf(text: str = "Test document content for status checking.") -> bytes:
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
        user_a = f"status_user_a_{unique_suffix}"
        user_b = f"status_user_b_{unique_suffix}"
        password = "strongpassword123"

        print(f"--- 1. Registering Users ({user_a}, {user_b}) ---")
        token_a = await get_test_token(client, user_a, password)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = await get_test_token(client, user_b, password)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        print("\n--- 2. Uploading Document as User A ---")
        pdf_bytes = make_test_pdf("Machine Learning Deep Dive and Agent Reasoning Research.")
        files = {"file": ("research_status.pdf", pdf_bytes, "application/pdf")}
        res_upload = await client.post("/api/documents/upload", files=files, headers=headers_a)
        print("User A Upload Status:", res_upload.status_code)
        upload_data = res_upload.json()
        print("User A Upload Response:", upload_data)
        assert res_upload.status_code == 200
        doc_id = upload_data["document_id"]
        assert doc_id is not None

        print(f"\n--- 3. Checking Document Status via GET /api/documents/{doc_id} as User A ---")
        # Poll document status until processed
        status_data = None
        for _ in range(10):
            res_status = await client.get(f"/api/documents/{doc_id}", headers=headers_a)
            assert res_status.status_code == 200
            status_data = res_status.json()
            if status_data["status"] in ["indexed", "failed"]:
                break
            await asyncio.sleep(0.5)

        print("Final Document Status Response:", status_data)
        assert status_data["id"] == doc_id
        assert status_data["filename"] == "research_status.pdf"
        assert status_data["status"] == "indexed"
        assert status_data["chunks"] >= 1
        assert status_data["error_message"] is None

        print(f"\n--- 4. Testing User Isolation: User B querying User A's document ({doc_id}) ---")
        res_isolation = await client.get(f"/api/documents/{doc_id}", headers=headers_b)
        print("User B Access Status:", res_isolation.status_code)
        print("User B Access Body:", res_isolation.json())
        assert res_isolation.status_code == 404
        assert res_isolation.json() == {
            "error": "document_not_found",
            "detail": "The requested document does not exist."
        }

        print("\n--- 5. Testing Non-Existent Document ID (999999) ---")
        res_nonexistent = await client.get("/api/documents/999999", headers=headers_a)
        print("Non-existent Document Status:", res_nonexistent.status_code)
        assert res_nonexistent.status_code == 404

        print("\n--- 6. Testing Failure State Tracking ---")
        corrupt_files = {"file": ("corrupt_status.pdf", b"%PDF-1.4 Empty Unparseable Content", "application/pdf")}
        res_corrupt_upload = await client.post("/api/documents/upload", files=corrupt_files, headers=headers_a)
        assert res_corrupt_upload.status_code == 200
        corrupt_doc_id = res_corrupt_upload.json()["document_id"]

        # Wait for background task to process and set failed status
        corrupt_status_data = None
        for _ in range(10):
            res_corrupt_status = await client.get(f"/api/documents/{corrupt_doc_id}", headers=headers_a)
            assert res_corrupt_status.status_code == 200
            corrupt_status_data = res_corrupt_status.json()
            if corrupt_status_data["status"] == "failed":
                break
            await asyncio.sleep(0.5)

        print("Corrupted Document Status Response:", corrupt_status_data)
        assert corrupt_status_data["id"] == corrupt_doc_id
        assert corrupt_status_data["status"] == "failed"
        assert corrupt_status_data["error_message"] is not None

    print("\n[Success] Document Status & Secure Document Access Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
