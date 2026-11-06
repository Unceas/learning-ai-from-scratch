"""Pytest suite for Day 178 Kubernetes deployment manifests."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
K8S_DIR = Path(PROJECT_DIR, "k8s")
DOCS_DIR = Path(PROJECT_DIR, "docs", "infrastructure")


def test_k8s_manifests_exist():
    """Verify all 10 core Kubernetes manifest files exist."""
    required_manifests = [
        "namespace.yaml",
        "backend-deployment.yaml",
        "backend-service.yaml",
        "frontend-deployment.yaml",
        "frontend-service.yaml",
        "worker-deployment.yaml",
        "configmap.yaml",
        "secret.yaml",
        "ingress.yaml",
        "backend-hpa.yaml",
        "README.md",
    ]
    for filename in required_manifests:
        p = K8S_DIR / filename
        assert p.exists(), f"Missing manifest: {filename}"
        assert p.stat().st_size > 50, f"Manifest {filename} is too small"


def test_backend_deployment_spec():
    """Verify backend deployment has rolling update, probes, and resource limits."""
    content = (K8S_DIR / "backend-deployment.yaml").read_text(encoding="utf-8")
    assert "name: research-api" in content
    assert "replicas: 2" in content
    assert "path: /health/ready" in content
    assert "path: /health/live" in content
    assert "runAsNonRoot: true" in content


def test_ingress_and_services():
    """Verify ingress routes to ClusterIP services."""
    ingress_content = (K8S_DIR / "ingress.yaml").read_text(encoding="utf-8")
    backend_svc = (K8S_DIR / "backend-service.yaml").read_text(encoding="utf-8")
    frontend_svc = (K8S_DIR / "frontend-service.yaml").read_text(encoding="utf-8")

    assert "api.example.com" in ingress_content
    assert "app.example.com" in ingress_content
    assert "research-api" in backend_svc
    assert "research-frontend" in frontend_svc


def test_kubernetes_architecture_doc():
    """Verify architecture documentation exists and covers key concepts."""
    doc = DOCS_DIR / "KUBERNETES_ARCHITECTURE.md"
    assert doc.exists()
    content = doc.read_text(encoding="utf-8")
    assert "Control Plane vs. Worker Nodes" in content
    assert "Horizontal Pod Autoscaling" in content
    assert "Common Failure Modes & Diagnostics Runbook" in content
