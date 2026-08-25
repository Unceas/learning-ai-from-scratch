import asyncio
import httpx
from backend.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing User Registration ---")
        res_reg = await client.post("/api/auth/register", json={
            "user_id": "auth_test_user",
            "password": "strongpassword123"
        })
        print("Register Status:", res_reg.status_code)
        print("Register Body:", res_reg.json())
        assert res_reg.status_code == 200
        token_data = res_reg.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        print("\n--- 2. Testing Duplicate User Registration (409 Conflict) ---")
        res_dup = await client.post("/api/auth/register", json={
            "user_id": "auth_test_user",
            "password": "strongpassword123"
        })
        print("Duplicate Register Status:", res_dup.status_code)
        assert res_dup.status_code == 409

        print("\n--- 3. Testing User Login ---")
        res_login = await client.post("/api/auth/login", json={
            "user_id": "auth_test_user",
            "password": "strongpassword123"
        })
        print("Login Status:", res_login.status_code)
        assert res_login.status_code == 200
        assert "access_token" in res_login.json()

        print("\n--- 4. Testing Invalid Password Login (401 Unauthorized) ---")
        res_bad_login = await client.post("/api/auth/login", json={
            "user_id": "auth_test_user",
            "password": "wrongpassword"
        })
        print("Bad Login Status:", res_bad_login.status_code)
        assert res_bad_login.status_code == 401

        print("\n--- 5. Testing Protected Endpoint Without Token (401/403) ---")
        res_unauth = await client.get("/api/documents/")
        print("Unauthenticated Status:", res_unauth.status_code)
        assert res_unauth.status_code in [401, 403]

        print("\n--- 6. Testing Protected Endpoint With Bearer Token ---")
        headers = {"Authorization": f"Bearer {token}"}
        res_auth_docs = await client.get("/api/documents/", headers=headers)
        print("Authenticated Documents Status:", res_auth_docs.status_code)
        print("Authenticated Documents Body:", res_auth_docs.json())
        assert res_auth_docs.status_code == 200
        assert "documents" in res_auth_docs.json()

    print("\n[Success] JWT Authentication Foundation Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
