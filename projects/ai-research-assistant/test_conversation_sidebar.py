"""Comprehensive integration test suite for Day 155: Conversation History & Sidebar.

Verifies:
1. Frontend build artifacts and conversation sidebar component file structure.
2. Hook lifecycle contract in useChat (state exports, dependencies, deletion logic).
3. Backend conversation API lifecycle (provisioning on first message, persistence across turns).
4. Conversation switching, retrieval of full message history, and ordered turns.
5. Conversation deletion and multi-tenant security isolation.
"""

import os
import asyncio
import httpx
from backend.main import app
from backend.services.auth_service import create_access_token


async def test_conversation_sidebar_and_history():
    print("=" * 60)
    print("   Test Suite: Day 155 — Conversation History & Sidebar   ")
    print("=" * 60)

    # 1. Verify Frontend Components and Build Artifacts
    print("\n--- 1. Verifying Sidebar Component and Build Artifacts ---")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    sidebar_file = os.path.join(frontend_dir, "src", "components", "sidebar", "ConversationSidebar.jsx")
    chat_page = os.path.join(frontend_dir, "src", "pages", "Chat.jsx")
    app_file = os.path.join(frontend_dir, "src", "App.jsx")
    use_chat_file = os.path.join(frontend_dir, "src", "hooks", "useChat.js")
    dist_index = os.path.join(frontend_dir, "dist", "index.html")

    assert os.path.exists(sidebar_file), f"Missing {sidebar_file}"
    assert os.path.exists(chat_page), f"Missing {chat_page}"
    assert os.path.exists(app_file), f"Missing {app_file}"
    assert os.path.exists(use_chat_file), f"Missing {use_chat_file}"
    assert os.path.exists(dist_index), f"Missing built dist/index.html at {dist_index}"

    with open(sidebar_file, "r", encoding="utf-8") as f:
        sb_code = f.read()
    assert "ConversationSidebar" in sb_code, "Sidebar component must be exported"
    assert "onNewChat" in sb_code, "Sidebar must support onNewChat callback"
    assert "onSelectConversation" in sb_code, "Sidebar must support onSelectConversation callback"
    assert "onDeleteConversation" in sb_code, "Sidebar must support onDeleteConversation callback"
    assert "active" in sb_code, "Sidebar must support active conversation indicator"

    with open(use_chat_file, "r", encoding="utf-8") as f:
        hook_code = f.read()
    assert "removeConversation" in hook_code, "useChat must export removeConversation"
    assert "conversationsLoading" in hook_code, "useChat must export conversationsLoading"
    assert "loadConversations" in hook_code, "useChat must export loadConversations"
    assert "deleteConversation" in hook_code, "useChat must import deleteConversation API"

    print("[PASSED] Component hierarchy, hook signatures, and production build verified.")

    test_user_a = "test_user_day155_a"
    test_user_b = "test_user_day155_b"
    token_a = create_access_token(test_user_a)
    token_b = create_access_token(test_user_b)
    auth_headers_a = {"Authorization": f"Bearer {token_a}"}
    auth_headers_b = {"Authorization": f"Bearer {token_b}"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000") as client:
        # 2. Initial Conversation Listing (Empty)
        print("\n--- 2. Initial Conversation Listing ---")
        res_list = await client.get("/api/conversations", headers=auth_headers_a)
        assert res_list.status_code == 200, f"Expected 200, got {res_list.status_code}"
        convs = res_list.json()
        assert isinstance(convs, list)
        print(f"[PASSED] Initial conversation count for user A: {len(convs)}")

        # 3. First Message Creates & Auto-Provisions Conversation
        print("\n--- 3. Sending First Message to Provision Conversation 1 ---")
        res_msg1 = await client.post(
            "/api/chat",
            json={"message": "What is self-attention mechanism?", "conversation_id": None},
            headers=auth_headers_a
        )
        assert res_msg1.status_code == 200
        data_msg1 = res_msg1.json()
        conv_id_1 = data_msg1.get("conversation_id")
        assert conv_id_1 is not None and isinstance(conv_id_1, int)
        print(f"[PASSED] Session 1 auto-provisioned with ID: {conv_id_1}")

        # 4. Verify Sidebar Shows Conversation 1
        print("\n--- 4. Verifying Sidebar Reflects Provisioned Conversation ---")
        res_list2 = await client.get("/api/conversations", headers=auth_headers_a)
        assert res_list2.status_code == 200
        convs2 = res_list2.json()
        found1 = any(c["id"] == conv_id_1 for c in convs2)
        assert found1, f"Conversation {conv_id_1} not found in sidebar list: {convs2}"
        print(f"[PASSED] Conversation {conv_id_1} found in user A sidebar list.")

        # 5. Follow-Up Message Uses Same Conversation ID
        print("\n--- 5. Sending Follow-up Message With Active conversation_id ---")
        res_msg2 = await client.post(
            "/api/chat",
            json={"message": "How does multi-head attention extend it?", "conversation_id": conv_id_1},
            headers=auth_headers_a
        )
        assert res_msg2.status_code == 200
        data_msg2 = res_msg2.json()
        assert data_msg2.get("conversation_id") == conv_id_1, "Must maintain active conversation ID"
        print(f"[PASSED] Maintained conversation ID {conv_id_1} across follow-up turn.")

        # 6. Verify Conversation Details & Message Retrieval Contract
        print("\n--- 6. Verifying Conversation Details Retrieval Contract ---")
        res_detail = await client.get(f"/api/conversations/{conv_id_1}", headers=auth_headers_a)
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["id"] == conv_id_1
        assert len(detail_data["messages"]) == 4, f"Expected 4 turns, got {len(detail_data['messages'])}"
        assert detail_data["messages"][0]["role"] == "user"
        assert detail_data["messages"][1]["role"] == "assistant"
        print(f"[PASSED] Retrieved 4 turns in order for conversation {conv_id_1}.")

        # 7. Create Second Conversation (Simulate '+ New Chat' Flow)
        print("\n--- 7. Starting Fresh Session 2 (+ New Chat) ---")
        res_msg3 = await client.post(
            "/api/chat",
            json={"message": "Explain BM25 Okapi lexical scoring.", "conversation_id": None},
            headers=auth_headers_a
        )
        assert res_msg3.status_code == 200
        conv_id_2 = res_msg3.json().get("conversation_id")
        assert conv_id_2 is not None and conv_id_2 != conv_id_1
        print(f"[PASSED] Session 2 auto-provisioned with fresh ID: {conv_id_2}")

        # Verify sidebar lists both conversations
        res_list3 = await client.get("/api/conversations", headers=auth_headers_a)
        convs3 = res_list3.json()
        ids = [c["id"] for c in convs3]
        assert conv_id_1 in ids and conv_id_2 in ids
        print(f"[PASSED] Sidebar lists both conversations: {ids}")

        # 8. Multi-Tenant Isolation
        print("\n--- 8. Verifying Multi-Tenant Isolation ---")
        # User B should not see User A's conversations in sidebar
        res_list_b = await client.get("/api/conversations", headers=auth_headers_b)
        convs_b = res_list_b.json()
        assert not any(c["id"] in (conv_id_1, conv_id_2) for c in convs_b), "User B leaked User A conversations"

        # User B cannot access or delete User A's conversation
        res_cross_get = await client.get(f"/api/conversations/{conv_id_1}", headers=auth_headers_b)
        assert res_cross_get.status_code == 404, f"Expected 404 for cross-user get, got {res_cross_get.status_code}"

        res_cross_del = await client.delete(f"/api/conversations/{conv_id_1}", headers=auth_headers_b)
        assert res_cross_del.status_code == 404, f"Expected 404 for cross-user delete, got {res_cross_del.status_code}"
        print("[PASSED] Multi-tenant isolation verified: cross-user access rejected with 404.")

        # 9. Delete Conversation 2
        print("\n--- 9. Deleting Conversation 2 ---")
        res_del = await client.delete(f"/api/conversations/{conv_id_2}", headers=auth_headers_a)
        assert res_del.status_code == 200
        assert res_del.json().get("status") == "deleted"

        # Verify Conversation 2 is gone from sidebar
        res_list4 = await client.get("/api/conversations", headers=auth_headers_a)
        ids_after = [c["id"] for c in res_list4.json()]
        assert conv_id_2 not in ids_after, f"Conversation {conv_id_2} still present in sidebar"
        assert conv_id_1 in ids_after, f"Conversation {conv_id_1} accidentally removed"
        print(f"[PASSED] Conversation {conv_id_2} deleted. Remaining active: {ids_after}")

    print("\n" + "=" * 60)
    print("   [SUCCESS] All Day 155 Conversation Sidebar Checks Passed!   ")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_conversation_sidebar_and_history())
