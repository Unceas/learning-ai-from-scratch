import asyncio
import subprocess
import sys
from sqlalchemy import inspect
from backend.database import engine
from backend.models import User, Document
import httpx
from backend.main import app


def test_alembic_migration_tables():
    print("--- 1. Testing Alembic Current Revision ---")
    proc = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True
    )
    print("Alembic Current Output:", proc.stdout.strip())
    assert proc.returncode == 0, f"Alembic current failed: {proc.stderr}"
    assert "head" in proc.stdout

    print("\n--- 2. Inspecting Migrated SQLite Schema ---")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print("Database Tables Found:", tables)
    assert "users" in tables, "users table must exist in migrated database"
    assert "documents" in tables, "documents table must exist in migrated database"
    assert "alembic_version" in tables, "alembic_version table must exist"
    columns = [col["name"] for col in inspector.get_columns("documents")]
    print("Documents Table Columns:", columns)
    assert "error_message" in columns, "error_message column must exist in documents table"


async def test_app_endpoints():
    print("\n--- 3. Testing Application API over Migrated Database ---")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        print("Health Check:", res_health.json())


def main():
    test_alembic_migration_tables()
    asyncio.run(test_app_endpoints())
    print("\n[Success] Alembic Database Migrations Verified Successfully!")


if __name__ == "__main__":
    main()
