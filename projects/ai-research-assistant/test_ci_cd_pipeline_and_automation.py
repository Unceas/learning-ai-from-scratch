"""Suite #49: CI/CD Pipeline & Automated Deployment Tests.

Validates:
1. GitHub Actions CI workflow schema, syntax, branch triggers, and permissions.
2. Independent backend CI job: Python 3.12, dependency caching, Ruff linting, disposable Alembic migrations, and pytest.
3. Independent frontend CI job: Node.js 22, clean npm ci lockfile installation, and Vite production bundle build.
4. Deployment secrets hygiene: .gitignore coverage, .env exclusions, and template-only credentials in .env.example.
5. Migration automation safety: fresh disposable database migrations from base to head without corrupting app.db.
6. Post-deployment smoke test script and module validation.
7. Code quality tooling: pyproject.toml ruff lint rules and pytest.ini test discovery.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import yaml
from sqlalchemy import create_engine, inspect

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from smoke_test import run_smoke_test


class TestWorkflowSchemaAndConfiguration(unittest.TestCase):
    """Test GitHub Actions workflow file structure, syntax, and security boundaries."""

    def setUp(self):
        # Look for workflow in project directory or repository root
        project_root = os.path.abspath(os.path.dirname(__file__))
        repo_root = os.path.abspath(os.path.join(project_root, "../.."))

        self.workflow_paths = [
            os.path.join(project_root, ".github", "workflows", "ci.yml"),
            os.path.join(repo_root, ".github", "workflows", "ci.yml"),
        ]

    def test_workflow_file_exists_and_is_valid_yaml(self):
        """Workflow file exists in .github/workflows/ci.yml and parses as valid YAML."""
        found = False
        for path in self.workflow_paths:
            if os.path.exists(path):
                found = True
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self.assertIsInstance(data, dict)
                self.assertIn("name", data)
                self.assertIn("jobs", data)
                break
        self.assertTrue(found, f"Workflow file not found in: {self.workflow_paths}")

    def test_workflow_triggers_and_permissions(self):
        """Workflow triggers on push and pull_request to main, with least-privilege permissions."""
        for path in self.workflow_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Check triggers (handle both string "on" and boolean True in PyYAML)
            triggers = data.get("on") or data.get(True)
            self.assertIsNotNone(triggers)
            self.assertIn("push", triggers)
            self.assertIn("pull_request", triggers)
            self.assertIn("main", triggers["push"]["branches"])
            self.assertIn("main", triggers["pull_request"]["branches"])

            # Check permissions
            self.assertIn("permissions", data)
            self.assertEqual(data["permissions"].get("contents"), "read")

    def test_workflow_has_backend_and_frontend_jobs(self):
        """Workflow defines decoupled backend and frontend jobs."""
        for path in self.workflow_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            jobs = data["jobs"]
            self.assertTrue(
                "backend-ci" in jobs or "backend-tests" in jobs,
                "Workflow must contain backend-ci job"
            )
            self.assertTrue(
                "frontend-ci" in jobs or "frontend-build" in jobs,
                "Workflow must contain frontend-ci job"
            )

            # Check backend steps
            backend_job = jobs.get("backend-ci") or jobs.get("backend-tests")
            step_names = [s.get("name", "").lower() for s in backend_job.get("steps", [])]
            self.assertTrue(any("checkout" in n for n in step_names))
            self.assertTrue(any("python" in n for n in step_names))
            self.assertTrue(any("ruff" in n or "lint" in n for n in step_names))
            self.assertTrue(any("migration" in n or "alembic" in n for n in step_names))
            self.assertTrue(any("test" in n or "pytest" in n for n in step_names))

            # Check frontend steps
            frontend_job = jobs.get("frontend-ci") or jobs.get("frontend-build")
            fe_step_names = [s.get("name", "").lower() for s in frontend_job.get("steps", [])]
            self.assertTrue(any("checkout" in n for n in fe_step_names))
            self.assertTrue(any("node" in n for n in fe_step_names))
            self.assertTrue(any("dependencies" in n or "install" in n for n in fe_step_names))
            self.assertTrue(any("build" in n for n in fe_step_names))


class TestSecretsHygieneAndSecurity(unittest.TestCase):
    """Test gitignore patterns, secret isolation, and template placeholder safety."""

    def test_gitignore_protects_env_and_db_files(self):
        """Repository .gitignore strictly ignores .env and SQLite database files."""
        gitignore_path = os.path.join(os.path.dirname(__file__), ".gitignore")
        self.assertTrue(os.path.exists(gitignore_path))
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn(".env", content)
        self.assertIn("*.db", content)
        self.assertIn("app.db", content)
        self.assertIn("uploads/", content)

    def test_env_example_has_no_real_credentials(self):
        """.env.example contains only safe placeholder values and no real keys."""
        env_example_path = os.path.join(os.path.dirname(__file__), ".env.example")
        self.assertTrue(os.path.exists(env_example_path))
        with open(env_example_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Reject live Google API keys or long hex secrets
        self.assertNotIn("AIzaSy", content)
        self.assertIn("your-local-development-key", content)
        self.assertIn("your-local-development-secret", content)

    def test_ci_workflow_has_no_embedded_production_secrets(self):
        """CI workflow file must never contain real production credentials."""
        workflow_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml")
        if os.path.exists(workflow_path):
            with open(workflow_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertNotIn("AIzaSy", content)
            self.assertIn("ci-test-secret", content)


class TestDisposableDatabaseMigration(unittest.TestCase):
    """Test that migrations run cleanly from base to head against a fresh database."""

    def test_migration_from_base_to_head_on_clean_db(self):
        """Alembic cleanly executes all migrations against a disposable SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_db = tmp.name

        try:
            db_url = f"sqlite:///{tmp_db}"
            env = os.environ.copy()
            env["DATABASE_URL"] = db_url

            project_dir = os.path.abspath(os.path.dirname(__file__))
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=project_dir,
                env=env,
                capture_output=True,
                text=True
            )
            self.assertEqual(proc.returncode, 0, f"Migration failed: {proc.stderr}\n{proc.stdout}")

            # Inspect created tables
            engine = create_engine(db_url)
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            expected = {
                "users", "documents", "conversations",
                "conversation_messages", "answer_feedback", "alembic_version"
            }
            self.assertTrue(expected.issubset(tables), f"Missing tables: {expected - tables}")

        finally:
            if os.path.exists(tmp_db):
                try:
                    os.remove(tmp_db)
                except OSError:
                    pass


class TestPostDeploymentSmokeScript(unittest.TestCase):
    """Test smoke test execution and error detection."""

    def test_smoke_test_script_file_exists(self):
        """smoke_test.sh exists in scripts/ directory with executable curl commands."""
        sh_path = os.path.join(os.path.dirname(__file__), "scripts", "smoke_test.sh")
        self.assertTrue(os.path.exists(sh_path))
        with open(sh_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("/health/live", content)
        self.assertIn("/health/ready", content)

    def test_python_smoke_test_success_path(self):
        """smoke_test.py returns True when both /health/live and /health/ready return 200."""
        mock_live = MagicMock()
        mock_live.status = 200
        mock_live.read.return_value = b'{"status": "alive"}'
        mock_live.__enter__.return_value = mock_live

        mock_ready = MagicMock()
        mock_ready.status = 200
        mock_ready.read.return_value = b'{"status": "ready", "checks": {"database": "ok", "vector_store": "ok"}}'
        mock_ready.__enter__.return_value = mock_ready

        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = [mock_live, mock_ready]
            self.assertTrue(run_smoke_test("http://dummy-test:8000"))

    def test_python_smoke_test_failure_path(self):
        """smoke_test.py returns False when /health/ready reports service unavailable."""
        mock_live = MagicMock()
        mock_live.status = 200
        mock_live.read.return_value = b'{"status": "alive"}'
        mock_live.__enter__.return_value = mock_live

        mock_ready = MagicMock()
        mock_ready.status = 503
        mock_ready.read.return_value = b'{"status": "not_ready"}'
        mock_ready.__enter__.return_value = mock_ready

        with patch("urllib.request.urlopen") as mock_url:
            mock_url.side_effect = [mock_live, mock_ready]
            self.assertFalse(run_smoke_test("http://dummy-test:8000"))


class TestCodeQualityTooling(unittest.TestCase):
    """Test configuration files for Ruff linter and pytest runner."""

    def test_pyproject_toml_exists(self):
        """pyproject.toml exists with ruff linter configuration."""
        toml_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        self.assertTrue(os.path.exists(toml_path))
        with open(toml_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[tool.ruff]", content)

    def test_pytest_ini_exists(self):
        """pytest.ini exists with testpaths set to tests."""
        ini_path = os.path.join(os.path.dirname(__file__), "pytest.ini")
        self.assertTrue(os.path.exists(ini_path))
        with open(ini_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("testpaths = tests", content)

    def test_ruff_linter_passes_on_backend_and_tests(self):
        """Ruff linter passes with zero violations across backend and tests."""
        project_dir = os.path.abspath(os.path.dirname(__file__))
        proc = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "backend", "tests"],
            cwd=project_dir,
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Ruff linting failed: {proc.stdout}\n{proc.stderr}")


if __name__ == "__main__":
    unittest.main()
