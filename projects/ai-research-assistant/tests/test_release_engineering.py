"""Unit tests validating release engineering artifacts, checklists, notes, and rollback procedures."""

import os
from unittest.mock import patch

from scripts.verify_release import SEMVER_REGEX, verify_release


def test_release_checklist_exists_and_contains_all_phases():
    """Verify RELEASE_CHECKLIST.md exists and covers all four operational gates."""
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "releases", "RELEASE_CHECKLIST.md")
    assert os.path.exists(doc_path), "RELEASE_CHECKLIST.md must exist in docs/releases/"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Pre-Release" in content
    assert "Staging Verification" in content
    assert "Production Release" in content
    assert "Rollback or Recovery" in content
    assert "Expand-and-Contract" in content
    assert "GET /health/live" in content
    assert "GET /health/ready" in content


def test_release_notes_template_structure():
    """Verify RELEASE_NOTES_TEMPLATE.md contains required section headings."""
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "releases", "RELEASE_NOTES_TEMPLATE.md")
    assert os.path.exists(doc_path), "RELEASE_NOTES_TEMPLATE.md must exist in docs/releases/"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    for heading in ["Added", "Changed", "Fixed", "Security", "Database Migrations", "Known Limitations", "Verification"]:
        assert heading.lower() in content.lower(), f"Missing heading: {heading}"


def test_rollback_strategy_documentation():
    """Verify ROLLBACK_STRATEGY.md covers multi-store recovery and expand-and-contract."""
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "releases", "ROLLBACK_STRATEGY.md")
    assert os.path.exists(doc_path), "ROLLBACK_STRATEGY.md must exist in docs/releases/"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Expand-and-Contract" in content
    assert "Phase A (Expand)" in content
    assert "Phase B (Migrate)" in content
    assert "Phase C (Contract)" in content
    assert "ChromaDB" in content
    assert "SQLite" in content
    assert "Rollback Triggers" in content


def test_v1_release_notes_integrity():
    """Verify v1.0.0.md release notes contain commit SHA and verified migration state."""
    doc_path = os.path.join(os.path.dirname(__file__), "..", "docs", "releases", "v1.0.0.md")
    assert os.path.exists(doc_path), "v1.0.0.md release notes must exist"

    with open(doc_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "v1.0.0" in content
    assert "56f8bdd" in content
    assert "0631c33b6ea9" in content


def test_semver_regex_validation():
    """Verify semantic versioning regex matches valid SemVer strings and rejects invalid ones."""
    valid_versions = ["1.0.0", "v1.0.0", "v1.2.3", "0.1.0", "v2.0.0-rc1"]
    for v in valid_versions:
        assert SEMVER_REGEX.match(v) is not None, f"Expected {v} to be valid SemVer"

    invalid_versions = ["1", "1.0", "v1", "version1", "alpha.1", ""]
    for inv in invalid_versions:
        assert SEMVER_REGEX.match(inv) is None, f"Expected {inv} to be invalid SemVer"


def test_verify_release_tool_pass():
    """Verify verify_release function passes for valid release candidate."""
    assert verify_release("v1.0.0") is True


def test_verify_release_health_gates_failure():
    """Verify verify_release reports failure when live health probe is unreachable."""
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        assert verify_release("v1.0.0", base_url="http://unreachable-host:9999") is False
