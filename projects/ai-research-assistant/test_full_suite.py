"""Comprehensive full test suite build check for AI Research Assistant backend & agent architecture."""

import subprocess
import sys

TEST_SCRIPTS = [
    "test_config.py",
    "test_api_validation.py",
    "test_fastapi_backend.py",
    "test_fastapi_chat.py",
    "test_document_indexing.py",
    "test_document_deduplication.py",
    "test_document_lifecycle.py",
    "test_user_isolation.py",
    "test_memory_lifecycle.py",
    "test_workflow.py",
    "test_multi_agent.py"
]


def run_all_tests():
    print("=" * 60)
    print("   AI Research Assistant - Full Build & Sync Verification   ")
    print("=" * 60)

    passed = 0
    failed = 0

    for script in TEST_SCRIPTS:
        print(f"\n[RUNNING] {script} ...")
        proc = subprocess.run([sys.executable, "-u", script], capture_output=True, text=True)

        if proc.returncode == 0:
            print(f"[PASSED] {script}")
            passed += 1
        else:
            print(f"[FAILED] {script}")
            print("STDOUT:\n", proc.stdout)
            print("STDERR:\n", proc.stderr)
            failed += 1

    print("\n" + "=" * 60)
    print(f"Summary: {passed} Passed, {failed} Failed out of {len(TEST_SCRIPTS)} Test Suites.")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
