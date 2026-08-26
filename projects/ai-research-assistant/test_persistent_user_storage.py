import asyncio
import os
import httpx
from backend.main import app
from backend.database import SessionLocal
from backend.models import User


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing User Registration & Persistence in SQLite ---")
        user_id = "sqlite_persist_user"
        password = "strongpassword123"

        res_reg = await client.post("/api/auth/register", json={
            "user_id": user_id,
            "password": password
        })
        print("Register Status:", res_reg.status_code)
        assert res_reg.status_code in [200, 409]

        print("\n--- 2. Direct Verification of SQLite Database Record ---")
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.id == user_id).first()
            assert db_user is not None, "User record must exist in SQLite database"
            print("Found User in SQLite Database:", db_user.id)
            print("Stored Password Hash:", db_user.password_hash[:20] + "...")
            assert db_user.password_hash != password, "Password must not be stored in plaintext"
            assert db_user.password_hash.startswith("$2b$") or db_user.password_hash.startswith("$2a$"), "Password must be bcrypt hash"
        finally:
            db.close()

        print("\n--- 3. Testing Login with Persistent Credentials ---")
        res_login = await client.post("/api/auth/login", json={
            "user_id": user_id,
            "password": password
        })
        print("Login Status:", res_login.status_code)
        assert res_login.status_code == 200
        token_data = res_login.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        print("Access Token Generated Successfully.")

        print("\n--- 4. Testing Duplicate User Registration (409 Conflict) ---")
        res_dup = await client.post("/api/auth/register", json={
            "user_id": user_id,
            "password": password
        })
        print("Duplicate Registration Status:", res_dup.status_code)
        assert res_dup.status_code == 409

        print("\n--- 5. Testing Bad Password Login (401 Unauthorized) ---")
        res_bad = await client.post("/api/auth/login", json={
            "user_id": user_id,
            "password": "wrongpassword"
        })
        print("Bad Login Status:", res_bad.status_code)
        assert res_bad.status_code == 401

    print("\n[Success] SQLite Persistent User Storage & Authentication Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
