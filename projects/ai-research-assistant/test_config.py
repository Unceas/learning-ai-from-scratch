import asyncio
import httpx
from backend.config import Settings, settings
from backend.main import app


async def main():
    print("--- 1. Testing Default Centralized Settings ---")
    print("App Name:", settings.app_name)
    print("App Version:", settings.app_version)
    print("Environment:", settings.environment)
    print("Chroma Path:", settings.chroma_path)
    print("Memory Path:", settings.memory_path)
    print("Embedding Model:", settings.embedding_model)
    print("Max Upload Size (MB):", settings.max_upload_size_mb)

    assert settings.app_name == "AI Research Assistant"
    assert settings.app_version == "1.0.0"
    assert settings.environment == "development"
    assert settings.chroma_path == "./document_db"
    assert settings.memory_path == "./memory_db"
    assert settings.embedding_model == "all-MiniLM-L6-v2"
    assert settings.max_upload_size_mb == 20

    print("\n--- 2. Testing Custom Environment Overrides ---")
    prod_settings = Settings(
        environment="production",
        chroma_path="/data/chroma",
        memory_path="/data/memory",
        embedding_model="all-MiniLM-L6-v2",
        max_upload_size_mb=50
    )
    assert prod_settings.environment == "production"
    assert prod_settings.chroma_path == "/data/chroma"
    assert prod_settings.max_upload_size_mb == 50
    print("Production Settings Instantiation Verified.")

    print("\n--- 3. Testing GET /health via ASGI Client ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health")
        print("Health Check Status:", res.status_code)
        print("Health Check Body:", res.json())
        assert res.status_code == 200
        assert res.json() == {
            "status": "healthy",
            "environment": "development"
        }

    print("\n[Success] Centralized Configuration & Health Endpoint Verified Successfully!")


if __name__ == "__main__":
    asyncio.run(main())
