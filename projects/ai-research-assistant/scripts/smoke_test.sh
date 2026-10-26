#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"

echo "Executing deployment smoke tests against ${API_BASE_URL}..."

echo "[1/2] Probing Liveness: ${API_BASE_URL}/health/live"
curl --fail --silent --show-error "${API_BASE_URL}/health/live"
echo ""

echo "[2/2] Probing Readiness: ${API_BASE_URL}/health/ready"
curl --fail --silent --show-error "${API_BASE_URL}/health/ready"
echo ""

echo "Smoke test passed successfully! Deployment is healthy and ready to serve traffic."
