import asyncio
import uuid
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.document_service import DocumentService


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
        test_user = f"bg_user_{uuid.uuid4().hex[:8]}"
        password = "strongpassword123"
        print(f"--- 1. Authenticating Test User: {test_user} ---")
        token = await get_test_token(client, test_user, password)
        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- 2. Testing Asynchronous Document Upload (Background Processing) ---")
        fake_pdf = b"%PDF-1.4 Asynchronous Background Document Ingestion with FastAPI BackgroundTasks."
        files = {"file": ("async_research.pdf", fake_pdf, "application/pdf")}

        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[{"page": 1, "text": "Background processing test content."}]):
            res_upload = await client.post("/api/documents/upload", files=files, headers=headers)
            print("Upload Response Status:", res_upload.status_code)
            upload_body = res_upload.json()
            print("Upload Response Body:", upload_body)
            assert res_upload.status_code == 200
            assert upload_body["status"] in ["processing", "indexed"]
            assert upload_body["filename"] == "async_research.pdf"
            assert "document_id" in upload_body

        print("\n--- 3. Verifying Document State via GET /api/documents/ ---")
        res_list = await client.get("/api/documents/", headers=headers)
        print("List Documents Status:", res_list.status_code)
        docs = res_list.json()["documents"]
        print("Documents Found:", docs)
        assert len(docs) == 1
        doc = docs[0]
        assert doc["filename"] == "async_research.pdf"
        assert doc["status"] in ["processing", "indexed"]
        file_hash = doc["file_hash"]

        print("\n--- 4. Testing Duplicate Document Upload ---")
        files_dup = {"file": ("async_research.pdf", fake_pdf, "application/pdf")}
        res_dup = await client.post("/api/documents/upload", files=files_dup, headers=headers)
        print("Duplicate Upload Response:", res_dup.json())
        assert res_dup.status_code == 200
        assert res_dup.json()["filename"] == "async_research.pdf"

        print("\n--- 5. Testing Failed Document Background Processing ---")
        corrupted_pdf = b"%PDF-1.4 corrupted empty file"
        files_corrupt = {"file": ("corrupt.pdf", corrupted_pdf, "application/pdf")}
        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[]):
            res_corrupt = await client.post("/api/documents/upload", files=files_corrupt, headers=headers)
            print("Corrupted Upload Response:", res_corrupt.json())
            assert res_corrupt.status_code == 200

        res_list_after_fail = await client.get("/api/documents/", headers=headers)
        failed_docs = [d for d in res_list_after_fail.json()["documents"] if d["filename"] == "corrupt.pdf"]
        assert len(failed_docs) == 1
        print("Failed Document Record:", failed_docs[0])
        assert failed_docs[0]["status"] == "failed"
        assert failed_docs[0]["error_message"] is not None

        print("\n--- 6. Testing Document Deletion Lifecycle ---")
        res_del = await client.delete(f"/api/documents/{file_hash}", headers=headers)
        print("Delete Response Status:", res_del.status_code)
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

    print("\n[Success] Background Document Processing & Error State Tracking Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
