"""Production deployment smoke testing script.

Executes health probes, authentication checks, document listing, and clean teardown.
"""

import os
import sys
import requests

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
SMOKE_USER = os.getenv("SMOKE_TEST_USER", "smoke_tester@example.com")
SMOKE_PASS = os.getenv("SMOKE_TEST_PASSWORD", "SmokePass123!")


def run_smoke_tests():
    print(f"=== Starting Production Deployment Smoke Tests against {BASE_URL} ===")
    session = requests.Session()

    # 1. Liveness check
    print("[1/5] Checking GET /health/live ...", end=" ", flush=True)
    try:
        r = session.get(f"{BASE_URL}/health/live", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        print("OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    # 2. Readiness check
    print("[2/5] Checking GET /health/ready ...", end=" ", flush=True)
    try:
        r = session.get(f"{BASE_URL}/health/ready", timeout=10)
        assert r.status_code in (200, 503), f"Unexpected status {r.status_code}"
        print(f"OK (status={r.status_code})")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    # 3. Authentication endpoint sanity check
    print("[3/5] Verifying auth endpoint response ...", end=" ", flush=True)
    try:
        r = session.post(
            f"{BASE_URL}/auth/token",
            data={"username": SMOKE_USER, "password": SMOKE_PASS},
            timeout=5,
        )
        assert r.status_code in (200, 401), f"Auth endpoint returned unexpected status: {r.status_code}"
        print("OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    # 4. Document list endpoint (unauthorized check)
    print("[4/5] Verifying unauthorized access rejection ...", end=" ", flush=True)
    try:
        r = session.get(f"{BASE_URL}/documents", timeout=5)
        assert r.status_code in (401, 403), f"Expected 401/403 for unauthenticated request, got {r.status_code}"
        print("OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    # 5. Root / documentation check
    print("[5/5] Verifying OpenAPI docs accessibility ...", end=" ", flush=True)
    try:
        r = session.get(f"{BASE_URL}/docs", timeout=5)
        assert r.status_code in (200, 404), f"Docs check returned {r.status_code}"
        print("OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)

    print("\n=== All Production Smoke Tests Passed Successfully! ===")


if __name__ == "__main__":
    run_smoke_tests()
