import asyncio
import uuid
import httpx
from backend.main import app


def make_test_pdf(text: str = "Database-Backed Document Management and RAG metadata content.") -> bytes:
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
        user_a = f"doc_db_user_a_{unique_suffix}"
        user_b = f"doc_db_user_b_{unique_suffix}"
        print(f"--- 1. Registering and Authenticating User A ({user_a}) and User B ({user_b}) ---")
        token_a = await get_test_token(client, user_a, "strongpassword123")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = await get_test_token(client, user_b, "strongpassword123")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        print("\n--- 2. Uploading Document as User A ---")
        pdf_bytes = make_test_pdf("Database-Backed Document Management and RAG metadata content.")
        files = {"file": ("research_paper.pdf", pdf_bytes, "application/pdf")}
        res_upload = await client.post("/api/documents/upload", files=files, headers=headers_a)
        print("User A Upload Status:", res_upload.status_code)
        print("User A Upload Body:", res_upload.json())
        assert res_upload.status_code == 200
        assert res_upload.json()["status"] in ["processing", "indexed", "already_indexed"]
        assert res_upload.json()["filename"] == "research_paper.pdf"

        print("\n--- 3. Listing Documents as User A ---")
        res_list_a = await client.get("/api/documents/", headers=headers_a)
        print("User A Documents Status:", res_list_a.status_code)
        docs_a = res_list_a.json()["documents"]
        print("User A Documents Count:", len(docs_a))
        assert len(docs_a) >= 1
        file_hash = docs_a[0]["file_hash"]
        assert docs_a[0]["filename"] == "research_paper.pdf"
        assert docs_a[0]["status"] in ["processing", "indexed"]

        print("\n--- 4. Testing Duplicate Upload as User A ---")
        files_dup = {"file": ("research_paper.pdf", pdf_bytes, "application/pdf")}
        res_dup = await client.post("/api/documents/upload", files=files_dup, headers=headers_a)
        print("Duplicate Upload Status:", res_dup.status_code)
        print("Duplicate Upload Body:", res_dup.json())
        assert res_dup.status_code == 200
        assert res_dup.json()["status"] in ["processing", "indexed", "already_indexed"]

        print("\n--- 5. Testing Multi-User Isolation (User B Perspective) ---")
        res_list_b = await client.get("/api/documents/", headers=headers_b)
        docs_b = res_list_b.json()["documents"]
        print("User B Documents Count:", len(docs_b))
        assert len(docs_b) == 0

        res_del_b = await client.delete(f"/api/documents/{file_hash}", headers=headers_b)
        print("User B Delete Attempt Status:", res_del_b.status_code)
        print("User B Delete Attempt Body:", res_del_b.json())
        assert res_del_b.status_code in [400, 404]
        assert res_del_b.json() == {
            "error": "document_not_found",
            "detail": "The requested document does not exist."
        }

        print("\n--- 6. Deleting Document as User A ---")
        res_del_a = await client.delete(f"/api/documents/{file_hash}", headers=headers_a)
        print("User A Delete Status:", res_del_a.status_code)
        print("User A Delete Body:", res_del_a.json())
        assert res_del_a.status_code == 200
        assert res_del_a.json()["status"] == "deleted"

        print("\n--- 7. Listing Documents After Deletion ---")
        res_list_a_after = await client.get("/api/documents/", headers=headers_a)
        docs_a_after = [d for d in res_list_a_after.json()["documents"] if d["file_hash"] == file_hash]
        assert len(docs_a_after) == 0
        print("User A Documents After Deletion:", res_list_a_after.json()["documents"])

    print("\n[Success] Database-Backed Document Management & User Isolation Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
