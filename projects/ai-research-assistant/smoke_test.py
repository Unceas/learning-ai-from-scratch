"""Post-deployment smoke test verifying liveness and readiness endpoints."""

import json
import os
import sys
import urllib.request


def run_smoke_test(base_url: str = "http://localhost:8000") -> bool:
    """Execute smoke test against target API URL, verifying /health/live and /health/ready."""
    print(f"Executing post-deployment smoke test against: {base_url}")
    success = True

    # 1. Test Liveness
    live_url = f"{base_url.rstrip('/')}/health/live"
    try:
        req = urllib.request.Request(live_url, headers={"User-Agent": "SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=5) as res:
            if res.status != 200:
                print(f"[FAIL] Liveness returned HTTP {res.status}")
                success = False
            else:
                body = json.loads(res.read().decode("utf-8"))
                if body.get("status") == "alive":
                    print(f"[PASS] Liveness probe OK: {body}")
                else:
                    print(f"[FAIL] Unexpected liveness body: {body}")
                    success = False
    except Exception as e:
        print(f"[FAIL] Liveness probe error: {e}")
        success = False

    # 2. Test Readiness
    ready_url = f"{base_url.rstrip('/')}/health/ready"
    try:
        req = urllib.request.Request(ready_url, headers={"User-Agent": "SmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status != 200:
                print(f"[FAIL] Readiness returned HTTP {res.status}")
                success = False
            else:
                body = json.loads(res.read().decode("utf-8"))
                if body.get("status") == "ready":
                    print(f"[PASS] Readiness probe OK: {body}")
                else:
                    print(f"[FAIL] Readiness probe reported not ready: {body}")
                    success = False
    except Exception as e:
        print(f"[FAIL] Readiness probe error: {e}")
        success = False

    return success


if __name__ == "__main__":
    target_url = os.getenv("API_BASE_URL", sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000")
    if not run_smoke_test(target_url):
        sys.exit(1)
    print("\nAll post-deployment health checks passed successfully!")
