"""Comprehensive integration test suite for Day 156: Application Shell & Navigation.

Verifies:
1. react-router-dom installation in frontend package.json.
2. Component hierarchy: Navigation, AppShell, LoadingState, ErrorState, EmptyState.
3. ChatContext and useChatContext state preservation provider.
4. App.jsx route definitions (BrowserRouter, AppShell, /chat, /documents, / redirect).
5. Production Vite build compilation artifacts.
6. Backend chat and document API coexistence under unified application shell.
"""

import json
import os
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


async def test_app_shell_and_navigation():
    print("=" * 60)
    print("   Test Suite: Day 156 — Application Shell & Navigation   ")
    print("=" * 60)

    # 1. Verify Package Dependencies & Production Build
    print("\n--- 1. Verifying react-router-dom & Build Artifacts ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    pkg_json_path = os.path.join(frontend_dir, "package.json")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")

    assert os.path.exists(pkg_json_path), f"Missing {pkg_json_path}"
    with open(pkg_json_path, "r", encoding="utf-8") as f:
        pkg_data = json.load(f)
    assert "react-router-dom" in pkg_data.get("dependencies", {}), "react-router-dom missing from dependencies"

    assert os.path.exists(dist_index), f"Missing built dist/index.html at {dist_index}"
    print("[PASSED] react-router-dom installed and dist/index.html compiled.")

    # 2. Verify Component Files
    print("\n--- 2. Verifying Shell, Navigation, & Common Components ---")
    nav_file = os.path.join(frontend_dir, "src", "components", "navigation", "Navigation.jsx")
    shell_file = os.path.join(frontend_dir, "src", "components", "navigation", "AppShell.jsx")
    loading_file = os.path.join(frontend_dir, "src", "components", "common", "LoadingState.jsx")
    error_file = os.path.join(frontend_dir, "src", "components", "common", "ErrorState.jsx")
    empty_file = os.path.join(frontend_dir, "src", "components", "common", "EmptyState.jsx")
    context_file = os.path.join(frontend_dir, "src", "context", "ChatContext.jsx")
    app_file = os.path.join(frontend_dir, "src", "App.jsx")
    main_file = os.path.join(frontend_dir, "src", "main.jsx")
    chat_file = os.path.join(frontend_dir, "src", "pages", "Chat.jsx")

    for fpath in [nav_file, shell_file, loading_file, error_file, empty_file, context_file, app_file, main_file, chat_file]:
        assert os.path.exists(fpath), f"Missing expected file: {fpath}"

    with open(nav_file, "r", encoding="utf-8") as f:
        nav_code = f.read()
    assert "NavLink" in nav_code
    assert 'to="/chat"' in nav_code
    assert 'to="/documents"' in nav_code

    with open(shell_file, "r", encoding="utf-8") as f:
        shell_code = f.read()
    assert "Outlet" in shell_code
    assert "Navigation" in shell_code

    with open(context_file, "r", encoding="utf-8") as f:
        ctx_code = f.read()
    assert "ChatProvider" in ctx_code
    assert "useChatContext" in ctx_code

    with open(main_file, "r", encoding="utf-8") as f:
        main_code = f.read()
    assert "ChatProvider" in main_code, "main.jsx must wrap App with ChatProvider"

    with open(app_file, "r", encoding="utf-8") as f:
        app_code = f.read()
    assert "BrowserRouter" in app_code
    assert "AppShell" in app_code
    assert 'path="/chat"' in app_code
    assert 'path="/documents"' in app_code
    assert 'Navigate to="/chat"' in app_code

    with open(chat_file, "r", encoding="utf-8") as f:
        chat_code = f.read()
    assert "useChatContext" in chat_code, "Chat.jsx must consume useChatContext"

    print("[PASSED] All shell, routing, context, and common state components verified.")

    # 3. Test Backend APIs Coexistence Under Shared Shell
    print("\n--- 3. Testing Backend Chat & Documents API Coexistence ---")
    test_user = "test_user_day156_shell"
    token = create_access_token(test_user)
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # Chat API check
        chat_res = await client.post(
            "/api/chat",
            json={"message": "What is the core idea of application shell architecture?", "conversation_id": None},
            headers=auth_headers
        )
        assert chat_res.status_code == 200, f"Expected 200 from chat API, got {chat_res.status_code}"
        chat_data = chat_res.json()
        conv_id = chat_data.get("conversation_id")
        assert conv_id is not None
        print(f"[PASSED] Chat workspace endpoint active: provisioned conversation {conv_id}")

        # Documents API check
        doc_res = await client.get("/api/documents", headers=auth_headers)
        assert doc_res.status_code == 200, f"Expected 200 from documents API, got {doc_res.status_code}"
        docs = doc_res.json()
        doc_list = docs if isinstance(docs, list) else docs.get("documents", [])
        assert isinstance(doc_list, list)
        print(f"[PASSED] Documents workspace endpoint active: retrieved {len(doc_list)} documents")

        # Conversations API check
        conv_res = await client.get(f"/api/conversations/{conv_id}", headers=auth_headers)
        assert conv_res.status_code == 200
        conv_details = conv_res.json()
        assert conv_details["id"] == conv_id
        print(f"[PASSED] Persistent conversation retrieved with {len(conv_details.get('messages', []))} messages")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Day 156 Application Shell Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_app_shell_and_navigation())
