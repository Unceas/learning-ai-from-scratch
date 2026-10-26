"""Unit tests validating database schema migrations from base to head against disposable databases."""

import os
import subprocess
import sys
import tempfile
from sqlalchemy import create_engine, inspect


def test_migration_fresh_database_to_head():
    """Verify that a brand new empty database migrates cleanly to Alembic head."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = tmp.name

    try:
        db_url = f"sqlite:///{temp_db_path}"
        env = os.environ.copy()
        env["DATABASE_URL"] = db_url

        # Run alembic upgrade head using subprocess in project root
        project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True
        )

        assert res.returncode == 0, f"Alembic upgrade failed: {res.stderr}\n{res.stdout}"

        # Inspect migrated schema
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())

        required_tables = {
            "users",
            "documents",
            "conversations",
            "conversation_messages",
            "answer_feedback",
            "alembic_version",
        }
        assert required_tables.issubset(tables), f"Missing tables: {required_tables - tables}"

        # Verify key columns
        doc_cols = {col["name"] for col in inspector.get_columns("documents")}
        assert "error_message" in doc_cols
        assert "storage_path" in doc_cols
        assert "index_version" in doc_cols
        assert "processing_attempts" in doc_cols

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except OSError:
                pass
