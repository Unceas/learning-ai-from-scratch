import asyncio
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.document_service import DocumentService


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Register and authenticate test user
        reg_res = await client.post("/api/auth/register", json={
            "user_id": "test_user_validation",
            "password": "strongpassword123"
        })
        if reg_res.status_code == 200:
            token = reg_res.json()["access_token"]
        else:
            login_res = await client.post("/api/auth/login", json={
                "user_id": "test_user_validation",
                "password": "strongpassword123"
            })
            token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("--- 1. Testing Empty Chat Query Validation (HTTP 422) ---")
        res_empty_query = await client.post("/api/chat/", json={"query": ""}, headers=headers)
        print("Empty Query Status:", res_empty_query.status_code)
        assert res_empty_query.status_code == 422

        print("\n--- 2. Testing Non-Existent Document Deletion (AppException 400) ---")
        res_missing_doc = await client.delete("/api/documents/non_existent_hash", headers=headers)
        print("Missing Document Status:", res_missing_doc.status_code)
        print("Missing Document Body:", res_missing_doc.json())
        assert res_missing_doc.status_code == 400
        assert res_missing_doc.json() == {
            "error": "document_not_found",
            "detail": "The requested document does not exist."
        }

        print("\n--- 3. Testing Non-PDF File Upload Validation (HTTP 400) ---")
        res_invalid_type = await client.post(
            "/api/documents/upload",
            files={"file": ("image.png", b"Fake PNG Content", "image/png")},
            headers=headers
        )
        print("Invalid Type Status:", res_invalid_type.status_code)
        assert res_invalid_type.status_code == 400

        print("\n--- 4. Testing Empty Document Extraction (Background Failed State) ---")
        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[]):
            res_empty_doc = await client.post(
                "/api/documents/upload",
                files={"file": ("empty.pdf", b"%PDF-1.4 Empty PDF", "application/pdf")},
                headers=headers
            )
            print("Empty Document Status:", res_empty_doc.status_code)
            print("Empty Document Body:", res_empty_doc.json())
            assert res_empty_doc.status_code == 200
            assert res_empty_doc.json()["status"] == "processing"

        res_list = await client.get("/api/documents/", headers=headers)
        empty_doc_record = [d for d in res_list.json()["documents"] if d["filename"] == "empty.pdf"][0]
        print("Empty Document Stored Record:", empty_doc_record)
        assert empty_doc_record["status"] == "failed"
        assert empty_doc_record["error_message"] is not None

        print("\n--- 5. Testing Oversized File Upload Validation (HTTP 413) ---")
        large_bytes = b"0" * (21 * 1024 * 1024)
        res_large = await client.post(
            "/api/documents/upload",
            files={"file": ("huge.pdf", large_bytes, "application/pdf")},
            headers=headers
        )
        print("Large File Status:", res_large.status_code)
        assert res_large.status_code == 413

        print("\n--- 6. Testing Valid Document Upload Schema ---")
        with patch("backend.services.document_service.extract_pdf_text_pages", return_value=[{"page": 1, "text": "Valid research document content."}]):
            res_valid = await client.post(
                "/api/documents/upload",
                files={"file": ("valid_sample.pdf", b"%PDF-1.4 Valid Document Content", "application/pdf")},
                headers=headers
            )
            print("Valid Upload Status:", res_valid.status_code)
            print("Valid Upload Body:", res_valid.json())
            assert res_valid.status_code == 200
            assert res_valid.json()["status"] in ["processing", "indexed", "already_indexed"]
            assert "filename" in res_valid.json()

    print("\n[Success] API Validation & Error Handling Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
