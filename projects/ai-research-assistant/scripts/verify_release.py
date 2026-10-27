"""Automated release verification script validating versioning, documentation, schema, and health gates."""

import argparse
import os
import re
import subprocess
import sys
import urllib.request
import json

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

SEMVER_REGEX = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def get_current_commit() -> str:
    """Retrieve full git commit SHA."""
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown-commit"


def verify_release(version: str, base_url: str = None) -> bool:
    """Execute pre-release and deployment gate checks."""
    print("==================================================")
    print(f"   Release Verification Gate: {version}           ")
    print("==================================================")
    all_passed = True

    # 1. SemVer Validation
    match = SEMVER_REGEX.match(version)
    if not match:
        print(f"[FAIL] Version '{version}' does not adhere to Semantic Versioning (vMAJOR.MINOR.PATCH)")
        all_passed = False
    else:
        norm_version = f"v{match.group(1)}.{match.group(2)}.{match.group(3)}"
        print(f"[PASS] Semantic version validated: {norm_version}")

    # 2. Commit SHA Recording
    commit_sha = get_current_commit()
    print(f"[PASS] Release commit SHA recorded: {commit_sha}")

    # 3. Documentation Integrity
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    checklist_path = os.path.join(project_dir, "docs", "releases", "RELEASE_CHECKLIST.md")
    rollback_path = os.path.join(project_dir, "docs", "releases", "ROLLBACK_STRATEGY.md")
    notes_path = os.path.join(project_dir, "docs", "releases", f"{version.lstrip('v')}.md")
    notes_v_path = os.path.join(project_dir, "docs", "releases", f"{version}.md")

    if os.path.exists(checklist_path):
        print(f"[PASS] Found release checklist: {checklist_path}")
    else:
        print(f"[FAIL] Missing release checklist: {checklist_path}")
        all_passed = False

    if os.path.exists(rollback_path):
        print(f"[PASS] Found rollback strategy: {rollback_path}")
    else:
        print(f"[FAIL] Missing rollback strategy: {rollback_path}")
        all_passed = False

    if os.path.exists(notes_path) or os.path.exists(notes_v_path):
        found_notes = notes_path if os.path.exists(notes_path) else notes_v_path
        print(f"[PASS] Found release notes: {found_notes}")
    else:
        print(f"[WARN] No release notes found for version '{version}' in docs/releases/")

    # 4. Config app_version synchronization
    try:
        from backend.config import get_settings
        settings = get_settings()
        clean_v = version.lstrip("v")
        if settings.app_version == clean_v:
            print(f"[PASS] backend/config.py app_version ({settings.app_version}) matches release version")
        else:
            print(f"[WARN] backend/config.py app_version ({settings.app_version}) differs from release ({clean_v})")
    except Exception as e:
        print(f"[WARN] Could not verify backend config app_version: {e}")

    # 5. Database Migration State
    try:
        res = subprocess.run(["alembic", "current"], cwd=project_dir, capture_output=True, text=True)
        if res.returncode == 0 and "head" in res.stdout:
            print(f"[PASS] Database schema is at Alembic head: {res.stdout.strip()}")
        else:
            print(f"[FAIL] Database schema is not at Alembic head: {res.stdout.strip()} {res.stderr.strip()}")
            all_passed = False
    except Exception as e:
        print(f"[FAIL] Failed executing alembic current check: {e}")
        all_passed = False

    # 6. Live Health Gates (if target base_url provided)
    if base_url:
        print(f"\n--- Checking Deployment Health Gates ({base_url}) ---")
        live_ok = False
        ready_ok = False
        try:
            req = urllib.request.Request(f"{base_url.rstrip('/')}/health/live")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                live_ok = (resp.status == 200 and data.get("status") == "alive")
        except Exception as e:
            print(f"[FAIL] Liveness probe error: {e}")

        try:
            req = urllib.request.Request(f"{base_url.rstrip('/')}/health/ready")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                ready_ok = (resp.status == 200 and data.get("status") == "ready")
        except Exception as e:
            print(f"[FAIL] Readiness probe error: {e}")

        if live_ok:
            print("[PASS] Health gate: /health/live OK")
        else:
            print("[FAIL] Health gate: /health/live failed")
            all_passed = False

        if ready_ok:
            print("[PASS] Health gate: /health/ready OK")
        else:
            print("[FAIL] Health gate: /health/ready failed")
            all_passed = False

    print("==================================================")
    if all_passed:
        print("RESULT: Release verification PASSED. Release is approved.")
    else:
        print("RESULT: Release verification FAILED. Blocked by health gates.")
    print("==================================================")
    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Research Assistant Release Verification Tool")
    parser.add_argument("version", nargs="?", default="v1.0.0", help="Target release version (e.g. v1.0.0)")
    parser.add_argument("--url", default=os.getenv("API_BASE_URL"), help="Target deployment URL for health check probing")
    args = parser.parse_args()

    if not verify_release(args.version, args.url):
        sys.exit(1)
