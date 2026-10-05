"""Test Suite #38: Frontend Authentication & Session Management (Day 158).

Validates:
1. Backend Auth Contract: register, login, /me profile hydration, invalid credentials.
2. Token Storage & API Client Authorization: Bearer token header injection and 401 signal.
3. Multi-Tenant Cross-User Isolation: User A cannot see or access User B's documents or conversations.
4. Authenticated Chat Execution: Chat queries succeed with user-scoped persistence.
5. Frontend Component Architecture & Routing Boundaries: ProtectedRoute, Login, Register, App.jsx.
"""

import asyncio
import os
import re
import uuid
import httpx
from backend.main import app


def test_frontend_files_structure():
    print("--- 1. Testing Frontend File Structure & Route Manifest ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fe_dir = os.path.join(base_dir, "frontend", "src")

    storage_file = os.path.join(fe_dir, "auth", "storage.js")
    auth_api_file = os.path.join(fe_dir, "api", "auth.js")
    auth_ctx_file = os.path.join(fe_dir, "context", "AuthContext.jsx")
    protected_route = os.path.join(fe_dir, "components", "auth", "ProtectedRoute.jsx")
    login_page = os.path.join(fe_dir, "pages", "Login.jsx")
    register_page = os.path.join(fe_dir, "pages", "Register.jsx")
    app_file = os.path.join(fe_dir, "App.jsx")
    nav_file = os.path.join(fe_dir, "components", "navigation", "Navigation.jsx")

    for path, desc in [
        (storage_file, "Token storage"),
        (auth_api_file, "Auth API client"),
        (auth_ctx_file, "AuthContext provider"),
        (protected_route, "ProtectedRoute boundary"),
        (login_page, "Login page"),
        (register_page, "Register page"),
        (app_file, "App.jsx routing"),
        (nav_file, "Navigation bar"),
    ]:
        assert os.path.exists(path), f"Missing required file: {desc} at {path}"

    with open(app_file, "r", encoding="utf-8") as f:
        app_content = f.read()
    assert "ProtectedRoute" in app_content
    assert 'path="/login"' in app_content
    assert 'path="/register"' in app_content
    assert 'path="/chat"' in app_content
    assert 'path="/documents"' in app_content

    with open(nav_file, "r", encoding="utf-8") as f:
        nav_content = f.read()
    assert "useAuth" in nav_content
    assert "navigation-user" in nav_content
    assert "Sign out" in nav_content or "logout" in nav_content

    print("Frontend file structure and route boundary manifest verified.")


async def test_backend_auth_lifecycle_and_me():
    print("\n--- 2. Testing Backend Auth Contract & /api/auth/me ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_name = f"researcher_{uuid.uuid4().hex[:6]}"
        password = "strong_password_123"

        # Register with username
        reg_res = await client.post("/api/auth/register", json={
            "username": user_name,
            "password": password
        })
        assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
        reg_data = reg_res.json()
        assert "access_token" in reg_data
        assert reg_data["token_type"] == "bearer"
        token = reg_data["access_token"]

        # Duplicate register
        dup_res = await client.post("/api/auth/register", json={
            "username": user_name,
            "password": password
        })
        assert dup_res.status_code == 409

        # Login
        login_res = await client.post("/api/auth/login", json={
            "username": user_name,
            "password": password
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()

        # Bad login
        bad_login = await client.post("/api/auth/login", json={
            "username": user_name,
            "password": "wrongpassword"
        })
        assert bad_login.status_code == 401

        # GET /api/auth/me without token
        unauth_me = await client.get("/api/auth/me")
        assert unauth_me.status_code in [401, 403]

        # GET /api/auth/me with token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200, f"/me failed: {me_res.text}"
        me_data = me_res.json()
        assert me_data["username"] == user_name
        assert me_data["id"] == user_name

        print("Auth registration, login, and /me endpoint verified.")


async def test_multi_tenant_user_isolation():
    print("\n--- 3. Testing Multi-Tenant Data Isolation (User A vs User B) ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        user_a = f"usera_{uuid.uuid4().hex[:6]}"
        user_b = f"userb_{uuid.uuid4().hex[:6]}"
        pwd = "securepassword123"

        # Register User A
        res_a = await client.post("/api/auth/register", json={"username": user_a, "password": pwd})
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Register User B
        res_b = await client.post("/api/auth/register", json={"username": user_b, "password": pwd})
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A creates a conversation
        conv_a_res = await client.post("/api/conversations", json={"title": "User A Research Session"}, headers=headers_a)
        assert conv_a_res.status_code in [200, 201]
        conv_a_id = conv_a_res.json()["id"]

        # User B fetches conversations -> User A's session must not be visible
        convs_b_res = await client.get("/api/conversations", headers=headers_b)
        assert convs_b_res.status_code == 200
        b_conv_ids = [c["id"] for c in convs_b_res.json()]
        assert conv_a_id not in b_conv_ids, "User B saw User A's conversation in list!"

        # User B attempts direct fetch of User A's conversation -> 404
        direct_conv_res = await client.get(f"/api/conversations/{conv_a_id}", headers=headers_b)
        assert direct_conv_res.status_code == 404, f"Cross-tenant access allowed! Got {direct_conv_res.status_code}"

        # User A uploads a minimal dummy document
        minimal_pdf = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 300 144]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
        )
        upload_a = await client.post(
            "/api/documents/upload",
            files={"file": ("usera_private.pdf", minimal_pdf, "application/pdf")},
            headers=headers_a
        )
        assert upload_a.status_code == 200
        doc_a_id = upload_a.json()["document_id"]

        # User B fetches documents -> User A's doc must not be visible
        docs_b_res = await client.get("/api/documents/", headers=headers_b)
        assert docs_b_res.status_code == 200
        b_doc_list = docs_b_res.json().get("documents", [])
        b_doc_ids = [d.get("id") or d.get("document_id") for d in b_doc_list]
        assert doc_a_id not in b_doc_ids, "User B saw User A's document in list!"

        # User B attempts direct status check of User A's document -> 404
        direct_doc_res = await client.get(f"/api/documents/{doc_a_id}", headers=headers_b)
        assert direct_doc_res.status_code == 404, f"Cross-tenant doc access allowed! Got {direct_doc_res.status_code}"

        print("Multi-tenant cross-user security boundaries verified (404 on unowned resources).")


async def test_authenticated_chat():
    print("\n--- 4. Testing Authenticated Chat Operations ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        chat_user = f"chatuser_{uuid.uuid4().hex[:6]}"
        reg = await client.post("/api/auth/register", json={"username": chat_user, "password": "password1234"})
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Chat request with auth token
        chat_res = await client.post(
            "/api/chat/",
            json={"query": "Hello, how do transformers process language?"},
            headers=headers
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "answer" in chat_data
        assert "conversation_id" in chat_data
        assert chat_data["conversation_id"] is not None

        # Verify conversation was saved under this user
        convs = await client.get("/api/conversations", headers=headers)
        assert convs.status_code == 200
        saved_ids = [c["id"] for c in convs.json()]
        assert chat_data["conversation_id"] in saved_ids

        print("Authenticated chat queries and conversation auto-provisioning verified.")


def main():
    test_frontend_files_structure()
    asyncio.run(test_backend_auth_lifecycle_and_me())
    asyncio.run(test_multi_tenant_user_isolation())
    asyncio.run(test_authenticated_chat())
    print("\n[SUCCESS] Day 158: Frontend Authentication & Session Management Verified Cleanly!")


if __name__ == "__main__":
    main()
