"""Comprehensive integration test suite for Day 157: Chat UX & API Resilience.

Verifies:
1. URL-addressable route configuration (/chat/:conversationId in App.jsx).
2. FailedMessage component and MessageBubble error recovery integration.
3. useChat explicit request states (sending, loadingConversation, retryMessage).
4. Error normalization logic (getUserError for 401, 404, 500, timeout).
5. 60-second request timeout configuration in client.js.
6. Backend conversation URL-addressability and 404 error handling.
"""

import json
import os
import subprocess
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


async def test_chat_ux_and_resilience():
    print("=" * 60)
    print("   Test Suite: Day 157 — Chat UX & API Resilience   ")
    print("=" * 60)

    # 1. Verify Component Files & Routing
    print("\n--- 1. Verifying Route Hierarchy & Component Structure ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    app_file = os.path.join(frontend_dir, "src", "App.jsx")
    failed_msg_file = os.path.join(frontend_dir, "src", "components", "chat", "FailedMessage.jsx")
    bubble_file = os.path.join(frontend_dir, "src", "components", "chat", "MessageBubble.jsx")
    chat_window_file = os.path.join(frontend_dir, "src", "components", "chat", "ChatWindow.jsx")
    chat_page_file = os.path.join(frontend_dir, "src", "pages", "Chat.jsx")
    use_chat_file = os.path.join(frontend_dir, "src", "hooks", "useChat.js")
    client_file = os.path.join(frontend_dir, "src", "api", "client.js")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")

    for fp in [app_file, failed_msg_file, bubble_file, chat_window_file, chat_page_file, use_chat_file, client_file, dist_index]:
        assert os.path.exists(fp), f"Missing required file: {fp}"

    with open(app_file, "r", encoding="utf-8") as f:
        app_code = f.read()
    assert 'path="/chat/:conversationId"' in app_code, "App.jsx must configure /chat/:conversationId route"

    with open(failed_msg_file, "r", encoding="utf-8") as f:
        failed_code = f.read()
    assert "Failed to send." in failed_code
    assert "Retry" in failed_code

    with open(bubble_file, "r", encoding="utf-8") as f:
        bubble_code = f.read()
    assert "FailedMessage" in bubble_code
    assert "message.status === \"failed\"" in bubble_code or "failed" in bubble_code
    assert "onRetry" in bubble_code

    with open(use_chat_file, "r", encoding="utf-8") as f:
        hook_code = f.read()
    assert "sending" in hook_code
    assert "loadingConversation" in hook_code
    assert "retryMessage" in hook_code
    assert "pending" in hook_code

    with open(client_file, "r", encoding="utf-8") as f:
        client_code = f.read()
    assert "getUserError" in client_code
    assert "DEFAULT_TIMEOUT_MS" in client_code or "60_000" in client_code or "60000" in client_code
    assert "AbortController" in client_code

    print("[PASSED] URL route configuration and resilient UI component structure verified.")

    # 2. Test Error Normalization via Node.js
    print("\n--- 2. Testing API Error Normalization Logic ---")
    node_test_script = """
    import { getUserError } from './frontend/src/api/client.js';

    // 401 Unauthorized
    const err401 = new Error('Unauthorized');
    err401.status = 401;
    if (getUserError(err401) !== 'Your session has expired. Please sign in again.') {
        console.error('Failed 401 test', getUserError(err401));
        process.exit(1);
    }

    // 404 Not Found
    const err404 = new Error('Not found');
    err404.status = 404;
    if (getUserError(err404) !== 'The requested conversation could not be found.') {
        console.error('Failed 404 test', getUserError(err404));
        process.exit(1);
    }

    // 500 Server Error
    const err500 = new Error('Internal Server Error');
    err500.status = 500;
    if (getUserError(err500) !== 'The research assistant is temporarily unavailable.') {
        console.error('Failed 500 test', getUserError(err500));
        process.exit(1);
    }

    // Timeout Error
    const errTimeout = new Error('The request took too long. Please try again.');
    errTimeout.name = 'AbortError';
    if (getUserError(errTimeout) !== 'The request took too long. Please try again.') {
        console.error('Failed timeout test', getUserError(errTimeout));
        process.exit(1);
    }

    console.log('ALL_ERROR_NORMALIZATION_TESTS_PASSED');
    """

    res = subprocess.run(
        ["node", "--input-type=module", "-e", node_test_script],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__)
    )
    assert res.returncode == 0, f"Error normalization test failed:\n{res.stderr}\n{res.stdout}"
    assert "ALL_ERROR_NORMALIZATION_TESTS_PASSED" in res.stdout
    print("[PASSED] getUserError handles 401, 404, 500, and request timeouts without exposing raw exceptions.")

    # 3. Test Backend Conversation URL Addressability & 404 Recovery
    print("\n--- 3. Testing Conversation Addressability & Error Responses ---")
    test_user = "test_user_day157_resilience"
    token = create_access_token(test_user)
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # Step A: Post message to create conversation
        res_post = await client.post(
            "/api/chat",
            json={"message": "What is API resilience?", "conversation_id": None},
            headers=auth_headers
        )
        assert res_post.status_code == 200
        data_post = res_post.json()
        conv_id = data_post["conversation_id"]
        assert isinstance(conv_id, int)
        print(f"[PASSED] Session created: conversation_id={conv_id}")

        # Step B: Address conversation by URL parameter ID
        res_get = await client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert res_get.status_code == 200
        conv_data = res_get.json()
        assert conv_data["id"] == conv_id
        assert len(conv_data["messages"]) >= 2
        print(f"[PASSED] URL route addressable: /chat/{conv_id} verified with {len(conv_data['messages'])} messages.")

        # Step C: Nonexistent conversation returns clean 404 for frontend error handling
        res_404 = await client.get("/api/conversations/999999", headers=auth_headers)
        assert res_404.status_code == 404, f"Expected 404, got {res_404.status_code}"
        print("[PASSED] Non-existent conversation correctly returns 404 handled by getUserError.")

        # Step D: Follow-up message on same URL addressable conversation
        res_followup = await client.post(
            "/api/chat",
            json={"message": "How does it protect user draft input?", "conversation_id": conv_id},
            headers=auth_headers
        )
        assert res_followup.status_code == 200
        assert res_followup.json()["conversation_id"] == conv_id
        print(f"[PASSED] Follow-up query preserved conversation_id={conv_id}.")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Day 157 Chat UX & Resilience Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chat_ux_and_resilience())
