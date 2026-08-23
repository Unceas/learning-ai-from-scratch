import asyncio
from unittest.mock import patch
import httpx
from backend.main import app
from backend.services.document_service import DocumentService


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing Invalid Empty Query (Validation Check) ---")
        res_empty = await client.post("/api/chat/", json={"query": ""})
        print("Empty Query Response Status:", res_empty.status_code)
        assert res_empty.status_code == 422, "Expected 422 Unprocessable Entity for empty query"

        print("\n--- 2. Testing Document Ingestion API ---")
        fake_pdf = b"%PDF-1.4 Artificial Intelligence and Machine Learning research content."
        files = {"file": ("test_doc.pdf", fake_pdf, "application/pdf")}
        with patch.object(DocumentService, 'extract_text', return_value=[{"page": 1, "text": "Artificial Intelligence and Machine Learning research content."}]):
            res_doc = await client.post("/api/documents/upload", files=files)
            print("Document Ingestion Response Status:", res_doc.status_code)
            print("Document Ingestion Body:", res_doc.json())
            assert res_doc.status_code == 200
            assert res_doc.json()["status"] in ["indexed", "already_indexed"]

        print("\n--- 3. Testing Valid Query via Chat API ---")
        res_chat = await client.post("/api/chat/", json={
            "query": "What is Artificial Intelligence?",
            "user_id": "test_user_ingest"
        })
        print("Chat Response Status:", res_chat.status_code)
        chat_data = res_chat.json()
        print("Chat Response Keys:", list(chat_data.keys()))
        assert res_chat.status_code == 200
        assert "answer" in chat_data
        assert "sources" in chat_data
        assert isinstance(chat_data["sources"], list)

    print("\n[Success] FastAPI Chat & Ingestion APIs Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
