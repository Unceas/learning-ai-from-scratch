import asyncio
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.document_service import DocumentService


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Registering and Authenticating User A and User B ---")
        reg_a = await client.post("/api/auth/register", json={
            "user_id": "doc_db_user_a",
            "password": "strongpassword123"
        })
        token_a = reg_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        reg_b = await client.post("/api/auth/register", json={
            "user_id": "doc_db_user_b",
            "password": "strongpassword123"
        })
        token_b = reg_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        print("\n--- 2. Uploading Document as User A ---")
        fake_pdf = b"%PDF-1.4 Artificial Intelligence Research Papers on Database-Backed RAG."
        files = {"file": ("research_paper.pdf", fake_pdf, "application/pdf")}
        with patch.object(DocumentService, 'extract_text', return_value=[{"page": 1, "text": "Database-Backed Document Management and RAG metadata content."}]):
            res_upload = await client.post("/api/documents/upload", files=files, headers=headers_a)
            print("User A Upload Status:", res_upload.status_code)
            print("User A Upload Body:", res_upload.json())
            assert res_upload.status_code == 200
            assert res_upload.json()["status"] == "indexed"
            assert res_upload.json()["filename"] == "research_paper.pdf"

        print("\n--- 3. Listing Documents as User A ---")
        res_list_a = await client.get("/api/documents/", headers=headers_a)
        print("User A Documents Status:", res_list_a.status_code)
        docs_a = res_list_a.json()["documents"]
        print("User A Documents Count:", len(docs_a))
        assert len(docs_a) == 1
        file_hash = docs_a[0]["file_hash"]
        assert docs_a[0]["filename"] == "research_paper.pdf"
        assert docs_a[0]["status"] == "indexed"

        print("\n--- 4. Testing Duplicate Upload as User A ---")
        files_dup = {"file": ("research_paper.pdf", fake_pdf, "application/pdf")}
        with patch.object(DocumentService, 'extract_text', return_value=[{"page": 1, "text": "Database-Backed Document Management and RAG metadata content."}]):
            res_dup = await client.post("/api/documents/upload", files=files_dup, headers=headers_a)
            print("Duplicate Upload Status:", res_dup.status_code)
            print("Duplicate Upload Body:", res_dup.json())
            assert res_dup.status_code == 200
            assert res_dup.json()["status"] == "already_indexed"

        print("\n--- 5. Testing Multi-User Isolation (User B Perspective) ---")
        # User B should see 0 documents
        res_list_b = await client.get("/api/documents/", headers=headers_b)
        docs_b = res_list_b.json()["documents"]
        print("User B Documents Count:", len(docs_b))
        assert len(docs_b) == 0

        # User B should not be able to delete User A's document
        res_del_b = await client.delete(f"/api/documents/{file_hash}", headers=headers_b)
        print("User B Delete Attempt Status:", res_del_b.status_code)
        print("User B Delete Attempt Body:", res_del_b.json())
        assert res_del_b.status_code == 400
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
        assert len(res_list_a_after.json()["documents"]) == 0
        print("User A Documents After Deletion:", res_list_a_after.json()["documents"])

    print("\n[Success] Database-Backed Document Management & User Isolation Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
