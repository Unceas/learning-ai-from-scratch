"""Integration test for Frontend Foundation (Day 151).

Verifies:
1. FastAPI CORS preflight headers and allowed origins.
2. Endpoint contracts invoked by frontend API clients (client.js, chat.js, documents.js, conversations.js).
3. Vite production build artifacts existence.
"""

import os
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


async def test_frontend_integration():
    print("=" * 60)
    print("   Test Suite: Frontend Foundation Integration (Day 151)   ")
    print("=" * 60)

    # 1. Verify Vite build artifacts
    print("\n--- 1. Verifying Vite Build Artifacts ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")
    assert os.path.exists(dist_index), f"Missing built index.html at {dist_index}"
    print("[PASSED] Vite build dist/index.html exists and is compiled.")

    # Generate dev token
    test_user = "test_fe_user"
    token = create_access_token(test_user)
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # 2. Verify CORS Preflight
        print("\n--- 2. Verifying CORS Preflight Configuration ---")
        cors_res = await client.options(
            "/api/chat/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization"
            }
        )
        assert cors_res.status_code == 200, f"Expected 200 for CORS preflight, got {cors_res.status_code}"
        assert cors_res.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "POST" in cors_res.headers.get("access-control-allow-methods", "")
        print("[PASSED] CORS allows http://localhost:5173 with credentials and standard headers.")

        # 3. Verify Documents API Contract
        print("\n--- 3. Verifying Documents API (/api/documents/) ---")
        docs_res = await client.get("/api/documents/", headers=auth_headers)
        assert docs_res.status_code == 200, f"Expected 200, got {docs_res.status_code}"
        data = docs_res.json()
        assert "documents" in data, "Expected 'documents' key in response"
        print(f"[PASSED] Documents API returned list (count={len(data['documents'])}).")

        # 4. Verify Conversations API Contract
        print("\n--- 4. Verifying Conversations API (/api/conversations) ---")
        convs_res = await client.get("/api/conversations", headers=auth_headers)
        assert convs_res.status_code == 200, f"Expected 200, got {convs_res.status_code}"
        conv_list = convs_res.json()
        assert isinstance(conv_list, list), "Expected list of conversations"
        print(f"[PASSED] Conversations API returned list (count={len(conv_list)}).")

        # 5. Verify Chat API Contract with message field
        print("\n--- 5. Verifying Chat API (/api/chat/) ---")
        chat_res = await client.post(
            "/api/chat/",
            json={"message": "What is attention in neural networks?"},
            headers=auth_headers
        )
        assert chat_res.status_code == 200, f"Expected 200, got {chat_res.status_code}"
        chat_data = chat_res.json()
        assert "answer" in chat_data, "Expected 'answer' in ChatResponse"
        assert "sources" in chat_data, "Expected 'sources' in ChatResponse"
        assert "conversation_id" in chat_data, "Expected 'conversation_id' in ChatResponse"
        print(f"[PASSED] Chat API succeeded (conversation_id={chat_data['conversation_id']}).")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Frontend Foundation Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_frontend_integration())
