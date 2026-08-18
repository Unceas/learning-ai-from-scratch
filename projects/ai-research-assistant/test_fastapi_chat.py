import asyncio
import io
import httpx
from backend.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing Invalid Empty Query (Validation Check) ---")
        res_empty = await client.post("/api/chat/", json={"query": ""})
        print("Empty Query Response Status:", res_empty.status_code)
        assert res_empty.status_code == 422, "Expected 422 Unprocessable Entity for empty query"

        print("\n--- 2. Testing Document Ingestion API ---")
        fake_txt = io.BytesIO(b"Artificial Intelligence and Machine Learning research content.")
        files = {"file": ("test_doc.txt", fake_txt, "text/plain")}
        data = {"user_id": "test_user_ingest"}
        res_doc = await client.post("/api/documents/upload", files=files, data=data)
        print("Document Ingestion Response Status:", res_doc.status_code)
        print("Document Ingestion Body:", res_doc.json())
        assert res_doc.status_code == 200
        assert res_doc.json()["status"] == "extracted"

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
