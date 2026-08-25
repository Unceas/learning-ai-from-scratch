import asyncio
import httpx
from backend.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("--- 1. Testing GET /health ---")
        res_health = await client.get("/health")
        print("Health Check Response:", res_health.status_code, res_health.json())
        assert res_health.status_code == 200
        assert res_health.json() == {"status": "healthy", "environment": "development"}

        print("\n--- 2. Registering and Authenticating Test User ---")
        reg_res = await client.post("/api/auth/register", json={
            "user_id": "fastapi_test_user",
            "password": "strongpassword123"
        })
        token = reg_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        print("\n--- 3. Testing POST /api/memory/ ---")
        res_mem = await client.post("/api/memory/", json={
            "text": "User prefers FastAPI and modular backend architecture.",
            "memory_type": "preference"
        }, headers=headers)
        print("Memory Creation Response:", res_mem.status_code, res_mem.json())
        assert res_mem.status_code == 200

        print("\n--- 4. Testing GET /api/memory/ ---")
        res_get_mem = await client.get("/api/memory/", params={"query": "FastAPI"}, headers=headers)
        print("Memory Retrieval Response:", res_get_mem.status_code, res_get_mem.json())
        assert res_get_mem.status_code == 200

        print("\n--- 5. Testing DELETE /api/memory/ ---")
        res_del_mem = await client.delete("/api/memory/", headers=headers)
        print("Memory Deletion Response:", res_del_mem.status_code, res_del_mem.json())
        assert res_del_mem.status_code == 200

    print("\n[Success] FastAPI Backend Architecture Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
