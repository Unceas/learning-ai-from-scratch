"""Suite #50: Release Engineering & Rollback Strategy Tests.

Validates:
1. Semantic versioning conventions and app_version alignment.
2. Complete release lifecycle documentation: RELEASE_CHECKLIST.md covering all four operational phases.
3. Release notes template and v1.0.0 release candidate documentation with recorded commit SHA.
4. Application rollback strategy: Expand-and-Contract database schema discipline, multi-store state recovery, and incident runbook.
5. Release health gates: readiness, error rates, latency thresholds, ingestion monitoring, and smoke test integration.
6. Automated release verification script (scripts/verify_release.py).
7. Immutable artifact tracking: commit SHA recording, dependency lockfiles, and migration lineage.
"""

import os
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.config import get_settings
from scripts.verify_release import SEMVER_REGEX, get_current_commit, verify_release


class TestSemanticVersioning(unittest.TestCase):
    """Test semantic versioning rules, configuration synchronization, and Git commit metadata."""

    def test_semver_pattern_matches_release_formats(self):
        """Semantic version regex correctly matches vX.Y.Z and X.Y.Z versions."""
        self.assertTrue(SEMVER_REGEX.match("1.0.0"))
        self.assertTrue(SEMVER_REGEX.match("v1.0.0"))
        self.assertTrue(SEMVER_REGEX.match("v1.2.3"))
        self.assertTrue(SEMVER_REGEX.match("v2.0.0-rc1"))

        self.assertIsNone(SEMVER_REGEX.match("1.0"))
        self.assertIsNone(SEMVER_REGEX.match("v1"))
        self.assertIsNone(SEMVER_REGEX.match("release-1.0.0"))

    def test_config_app_version_is_valid_semver(self):
        """backend/config.py app_version adheres to Semantic Versioning."""
        settings = get_settings()
        self.assertIsNotNone(settings.app_version)
        self.assertTrue(bool(SEMVER_REGEX.match(settings.app_version)))

    def test_current_commit_sha_retrieval(self):
        """Commit SHA is retrievable from Git environment."""
        sha = get_current_commit()
        self.assertIsInstance(sha, str)
        self.assertTrue(len(sha) >= 7)


class TestReleaseChecklistArtifacts(unittest.TestCase):
    """Test release checklist, release notes template, and v1.0.0 release notes."""

    def setUp(self):
        self.project_dir = os.path.abspath(os.path.dirname(__file__))
        self.docs_dir = os.path.join(self.project_dir, "docs", "releases")

    def test_release_checklist_contains_all_four_phases(self):
        """RELEASE_CHECKLIST.md must exist and define all 4 release lifecycle gates."""
        checklist_path = os.path.join(self.docs_dir, "RELEASE_CHECKLIST.md")
        self.assertTrue(os.path.exists(checklist_path), f"Missing {checklist_path}")

        with open(checklist_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("1. Pre-Release", content)
        self.assertIn("2. Staging Verification", content)
        self.assertIn("3. Production Release", content)
        self.assertIn("4. Rollback or Recovery", content)
        self.assertIn("Expand-and-Contract", content)
        self.assertIn("/health/live", content)
        self.assertIn("/health/ready", content)

    def test_release_notes_template_sections(self):
        """RELEASE_NOTES_TEMPLATE.md must specify all required reporting categories."""
        template_path = os.path.join(self.docs_dir, "RELEASE_NOTES_TEMPLATE.md")
        self.assertTrue(os.path.exists(template_path), f"Missing {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        for heading in ["Added", "Changed", "Fixed", "Security", "Database Migrations", "Known Limitations", "Verification"]:
            self.assertIn(heading, content)

    def test_v1_release_notes_integrity(self):
        """v1.0.0.md documents initial production baseline with commit SHA and migrations."""
        notes_path = os.path.join(self.docs_dir, "v1.0.0.md")
        self.assertTrue(os.path.exists(notes_path), f"Missing {notes_path}")

        with open(notes_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("v1.0.0", content)
        self.assertIn("56f8bdd", content)
        self.assertIn("0631c33b6ea9", content)
        self.assertIn("Hybrid candidate retrieval", content)


class TestRollbackStrategyAndStateRecovery(unittest.TestCase):
    """Test application rollback documentation, multi-store recovery, and Expand-and-Contract."""

    def setUp(self):
        self.project_dir = os.path.abspath(os.path.dirname(__file__))
        self.rollback_path = os.path.join(self.project_dir, "docs", "releases", "ROLLBACK_STRATEGY.md")

    def test_rollback_strategy_file_exists(self):
        """ROLLBACK_STRATEGY.md must exist in docs/releases/."""
        self.assertTrue(os.path.exists(self.rollback_path))

    def test_expand_and_contract_pattern_documented(self):
        """Rollback strategy documents Phase A (Expand), Phase B (Migrate), and Phase C (Contract)."""
        with open(self.rollback_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Expand-and-Contract", content)
        self.assertIn("Phase A (Expand)", content)
        self.assertIn("Phase B (Migrate)", content)
        self.assertIn("Phase C (Contract)", content)

    def test_multi_store_recovery_documented(self):
        """Rollback strategy addresses state recovery across relational DB, ChromaDB, and storage."""
        with open(self.rollback_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("SQLite", content)
        self.assertIn("ChromaDB", content)
        self.assertIn("File Storage", content)
        self.assertIn("delete_by_document_id", content)

    def test_rollback_triggers_defined(self):
        """Rollback strategy defines explicit health triggers and evaluation window."""
        with open(self.rollback_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("Rollback Triggers", content)
        self.assertIn("Readiness", content)
        self.assertIn("5xx", content)
        self.assertIn("Latency", content)


class TestReleaseVerificationTool(unittest.TestCase):
    """Test automated release verification gate script."""

    def test_verify_release_passes_for_current_repo(self):
        """verify_release approves release candidate v1.0.0 on current repository."""
        self.assertTrue(verify_release("v1.0.0"))

    def test_verify_release_rejects_invalid_version(self):
        """verify_release rejects non-SemVer version format."""
        self.assertFalse(verify_release("invalid-version"))

    def test_verify_release_evaluates_health_gates(self):
        """verify_release reports failure when live health endpoint check fails."""
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            self.assertFalse(verify_release("v1.0.0", base_url="http://dummy-nonexistent:9000"))


if __name__ == "__main__":
    unittest.main()
