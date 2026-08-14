import asyncio
import httpx
from backend.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing Invalid Empty Query (Validation Check) ---")
        res_empty = await client.post("/api/chat/", json={"query": ""})
        print("Empty Query Response Status:", res_empty.status_code)
        assert res_empty.status_code == 422, "Expected 422 Unprocessable Entity for empty query"

        print("\n--- 2. Testing Valid Query via Chat API ---")
        res_chat = await client.post("/api/chat/", json={
            "query": "What is Retrieval-Augmented Generation?",
            "user_id": "development-user"
        })
        print("Chat Response Status:", res_chat.status_code)
        print("Chat Response Body:", res_chat.json())
        assert res_chat.status_code == 200
        data = res_chat.json()
        assert "answer" in data
        assert "sources" in data
        assert isinstance(data["sources"], list)

    print("\n[Success] FastAPI Chat Endpoint Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
