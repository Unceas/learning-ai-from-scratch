import asyncio
import os
from pathlib import Path
import uuid
import httpx
from backend.storage.local import LocalStorage
from backend.storage.factory import get_storage
from backend.database import SessionLocal
from backend.models import Document
from backend.main import app


def make_test_pdf(text: str = "Storage Abstraction Unit & Integration Test Content.") -> bytes:
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


def test_storage_unit():
    print("--- 1. Testing LocalStorage save and delete directly ---")
    storage = LocalStorage(base_path="test_uploads_tmp")
    test_content = b"Unit test storage content"
    saved_path = storage.save("test_file.txt", test_content)
    print("Saved Path:", saved_path)
    assert Path(saved_path).exists()
    assert Path(saved_path).read_bytes() == test_content

    storage.delete(saved_path)
    assert not Path(saved_path).exists()
    print("Direct Storage save and delete verified.")

    # Clean up directory if empty
    Path("test_uploads_tmp").rmdir()


def test_storage_factory():
    print("\n--- 2. Testing Storage Factory ---")
    s = get_storage()
    assert isinstance(s, LocalStorage)
    print("Storage Factory instantiated:", type(s).__name__)


async def test_storage_api_lifecycle():
    print("\n--- 3. Testing Upload & Storage Integration via API ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        unique_suffix = uuid.uuid4().hex[:6]
        user = f"storage_user_{unique_suffix}"
        password = "strongpassword123"

        token = await get_test_token(client, user, password)
        headers = {"Authorization": f"Bearer {token}"}

        pdf_bytes = make_test_pdf("Storage Abstraction Full Pipeline Document Content.")
        files = {"file": ("storage_paper.pdf", pdf_bytes, "application/pdf")}

        res_upload = await client.post("/api/documents/upload", files=files, headers=headers)
        assert res_upload.status_code == 200
        upload_data = res_upload.json()
        doc_id = upload_data["document_id"]
        print("Upload Response:", upload_data)

        # Inspect database to verify storage_path was recorded
        db = SessionLocal()
        try:
            doc_record = db.query(Document).filter(Document.id == doc_id).first()
            assert doc_record is not None
            stored_file_path = doc_record.storage_path
            print("Recorded storage_path in SQLite:", stored_file_path)
            assert stored_file_path != ""
            assert Path(stored_file_path).exists()
            file_hash = doc_record.file_hash
        finally:
            db.close()

        # Wait for background task to finish
        print("\n--- 4. Polling Document Status ---")
        for _ in range(10):
            res_status = await client.get(f"/api/documents/{doc_id}", headers=headers)
            assert res_status.status_code == 200
            data = res_status.json()
            if data["status"] in ["indexed", "failed"]:
                break
            await asyncio.sleep(0.5)

        assert data["status"] == "indexed"
        print("Indexed Document Status:", data)

        # Confirm original file remains in storage after processing
        assert Path(stored_file_path).exists()
        print("Original file preserved in storage after indexing:", stored_file_path)

        # Test deletion: cleans up database, vector store, and physical storage
        print("\n--- 5. Deleting Document and Verifying Storage Cleanup ---")
        res_del = await client.delete(f"/api/documents/{file_hash}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

        # Verify physical file was deleted by storage abstraction
        assert not Path(stored_file_path).exists()
        print("Physical file successfully purged from storage on document delete.")


def main():
    test_storage_unit()
    test_storage_factory()
    asyncio.run(test_storage_api_lifecycle())
    print("\n[Success] Storage Abstraction Layer Verified Successfully!")


if __name__ == "__main__":
    main()
