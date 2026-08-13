from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("--- 1. Testing GET /health ---")
res_health = client.get("/health")
print("Health Check Response:", res_health.status_code, res_health.json())
assert res_health.status_code == 200
assert res_health.json() == {"status": "healthy"}

print("\n--- 2. Testing POST /api/memory/ ---")
res_mem = client.post("/api/memory/", json={
    "text": "User prefers FastAPI and modular backend architecture.",
    "memory_type": "preference",
    "user_id": "fastapi_test_user"
})
print("Memory Creation Response:", res_mem.status_code, res_mem.json())
assert res_mem.status_code == 200

print("\n--- 3. Testing GET /api/memory/ ---")
res_get_mem = client.get("/api/memory/", params={"query": "FastAPI", "user_id": "fastapi_test_user"})
print("Memory Retrieval Response:", res_get_mem.status_code, res_get_mem.json())
assert res_get_mem.status_code == 200

print("\n--- 4. Testing DELETE /api/memory/ ---")
res_del_mem = client.delete("/api/memory/", params={"user_id": "fastapi_test_user"})
print("Memory Deletion Response:", res_del_mem.status_code, res_del_mem.json())
assert res_del_mem.status_code == 200

print("\n[Success] FastAPI Backend Architecture Verified Successfully!")
