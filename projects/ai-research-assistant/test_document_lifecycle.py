import asyncio
import io
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.document_service import DocumentService
from backend.services.document_hash import calculate_file_hash


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and authenticate test user
        reg_res = await client.post("/api/auth/register", json={
            "user_id": "lifecycle_test_user",
            "password": "strongpassword123"
        })
        if reg_res.status_code == 200:
            token = reg_res.json()["access_token"]
        else:
            login_res = await client.post("/api/auth/login", json={
                "user_id": "lifecycle_test_user",
                "password": "strongpassword123"
            })
            token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("--- 1. Testing GET /api/documents/ (Initial List) ---")
        res_list1 = await client.get("/api/documents/", headers=headers)
        print("Initial List Response Status:", res_list1.status_code)
        assert res_list1.status_code == 200
        docs1 = res_list1.json().get("documents", [])
        print("Initial Documents Count:", len(docs1))

        print("\n--- 2. Indexing Test Document via DocumentService ---")
        service = DocumentService()
        pdf_bytes = b"Sample Document Management API Lifecycle Content."
        file_stream = io.BytesIO(pdf_bytes)
        file_hash = calculate_file_hash(file_stream)

        with patch.object(service, 'extract_text', return_value=[{"page": 1, "text": "Sample Document Lifecycle Content"}]):
            res_idx = service.index_document(file_stream, user_id="lifecycle_test_user", filename="lifecycle_sample.pdf")
            print("Index Result:", res_idx)

        print("\n--- 3. Testing GET /api/documents/ (After Indexing) ---")
        res_list2 = await client.get("/api/documents/", headers=headers)
        print("List After Indexing:", res_list2.json())
        assert res_list2.status_code == 200
        docs2 = res_list2.json().get("documents", [])
        matched = [d for d in docs2 if d["file_hash"] == file_hash]
        assert len(matched) == 1, "Expected indexed document to appear in registry list"

        print("\n--- 4. Testing DELETE /api/documents/{file_hash} ---")
        res_del = await client.delete(f"/api/documents/{file_hash}", headers=headers)
        print("Delete Response Status:", res_del.status_code)
        print("Delete Response Body:", res_del.json())
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

        print("\n--- 5. Testing DELETE Non-Existent Document (AppException Error Check) ---")
        res_del_404 = await client.delete("/api/documents/non_existent_hash_123", headers=headers)
        print("AppException Delete Status:", res_del_404.status_code)
        print("AppException Delete Body:", res_del_404.json())
        assert res_del_404.status_code in [400, 404]
        assert res_del_404.json() == {
            "error": "document_not_found",
            "detail": "The requested document does not exist."
        }

        print("\n--- 6. Testing GET /api/documents/ (After Deletion) ---")
        res_list3 = await client.get("/api/documents/", headers=headers)
        docs3 = res_list3.json().get("documents", [])
        matched3 = [d for d in docs3 if d["file_hash"] == file_hash]
        assert len(matched3) == 0, "Expected deleted document to be removed from registry list"

    print("\n[Success] Document Management Lifecycle API Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
