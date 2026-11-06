"""Suite #58: Kubernetes & Container Orchestration Tests.

Validates:
1. Namespace configuration isolating research-assistant workloads.
2. Backend deployment with replicas, rolling updates, resources, probes, and securityContext.
3. Backend ClusterIP service providing stable internal endpoint on port 8000.
4. Frontend deployment and service serving React SPA on port 80.
5. Decoupled worker deployment for background processing with dedicated resources.
6. Externalized configuration via ConfigMap and credentials template via Secret.
7. Ingress routing mapping external hostnames to internal services.
8. Horizontal Pod Autoscaler (HPA) targeting CPU utilization.
9. Architectural documentation and operational troubleshooting runbook.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path and is current working directory
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)


class TestKubernetesAndContainerOrchestration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proj_dir = Path(PROJECT_DIR)
        cls.k8s_dir = cls.proj_dir / "k8s"
        cls.docs_dir = cls.proj_dir / "docs" / "infrastructure"

    # ========================================================================
    # 1. Namespace Manifest Verification
    # ========================================================================

    def test_namespace_manifest(self):
        """K8S-001: namespace.yaml creates the research-assistant namespace."""
        manifest_path = self.k8s_dir / "namespace.yaml"
        self.assertTrue(manifest_path.exists(), "namespace.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")
        self.assertIn("kind: Namespace", content)
        self.assertIn("name: research-assistant", content)

    # ========================================================================
    # 2. Backend Deployment Verification
    # ========================================================================

    def test_backend_deployment_manifest(self):
        """K8S-002: backend-deployment.yaml defines 2 replicas, rolling updates, probes, and limits."""
        manifest_path = self.k8s_dir / "backend-deployment.yaml"
        self.assertTrue(manifest_path.exists(), "backend-deployment.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")

        self.assertIn("kind: Deployment", content)
        self.assertIn("name: research-api", content)
        self.assertIn("namespace: research-assistant", content)
        self.assertIn("replicas: 2", content)
        self.assertIn("type: RollingUpdate", content)
        self.assertIn("maxSurge: 1", content)
        self.assertIn("maxUnavailable: 0", content)
        self.assertIn("image: research-api:1.0.0", content)
        self.assertIn("containerPort: 8000", content)
        self.assertIn("configMapRef:", content)
        self.assertIn("name: research-config", content)
        self.assertIn("secretRef:", content)
        self.assertIn("name: research-secrets", content)

        # Resource bounds
        self.assertIn("cpu: \"250m\"", content)
        self.assertIn("memory: \"512Mi\"", content)
        self.assertIn("cpu: \"1\"", content)
        self.assertIn("memory: \"1Gi\"", content)

        # Health probes
        self.assertIn("path: /health/ready", content)
        self.assertIn("path: /health/live", content)

        # Security context
        self.assertIn("runAsNonRoot: true", content)
        self.assertIn("runAsUser: 1000", content)

    # ========================================================================
    # 3. Backend Service Verification
    # ========================================================================

    def test_backend_service_manifest(self):
        """K8S-003: backend-service.yaml exposes research-api on port 8000 via ClusterIP."""
        manifest_path = self.k8s_dir / "backend-service.yaml"
        self.assertTrue(manifest_path.exists(), "backend-service.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")

        self.assertIn("kind: Service", content)
        self.assertIn("name: research-api", content)
        self.assertIn("type: ClusterIP", content)
        self.assertIn("app: research-api", content)
        self.assertIn("port: 8000", content)
        self.assertIn("targetPort: 8000", content)

    # ========================================================================
    # 4. Frontend Deployment & Service Verification
    # ========================================================================

    def test_frontend_deployment_and_service(self):
        """K8S-004: frontend-deployment.yaml and frontend-service.yaml define SPA workload."""
        deploy_path = self.k8s_dir / "frontend-deployment.yaml"
        svc_path = self.k8s_dir / "frontend-service.yaml"
        self.assertTrue(deploy_path.exists(), "frontend-deployment.yaml is missing")
        self.assertTrue(svc_path.exists(), "frontend-service.yaml is missing")

        deploy_content = deploy_path.read_text(encoding="utf-8")
        self.assertIn("name: research-frontend", deploy_content)
        self.assertIn("image: research-frontend:1.0.0", deploy_content)
        self.assertIn("containerPort: 80", deploy_content)
        self.assertIn("readinessProbe:", deploy_content)
        self.assertIn("livenessProbe:", deploy_content)

        svc_content = svc_path.read_text(encoding="utf-8")
        self.assertIn("name: research-frontend", svc_content)
        self.assertIn("type: ClusterIP", svc_content)
        self.assertIn("port: 80", svc_content)
        self.assertIn("targetPort: 80", svc_content)

    # ========================================================================
    # 5. Background Worker Deployment Verification
    # ========================================================================

    def test_worker_deployment_manifest(self):
        """K8S-005: worker-deployment.yaml defines decoupled ingestion workers."""
        manifest_path = self.k8s_dir / "worker-deployment.yaml"
        self.assertTrue(manifest_path.exists(), "worker-deployment.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")

        self.assertIn("kind: Deployment", content)
        self.assertIn("name: document-worker", content)
        self.assertIn("image: research-api:1.0.0", content)
        self.assertIn("backend.worker", content)
        self.assertIn("configMapRef:", content)
        self.assertIn("secretRef:", content)
        self.assertIn("cpu: \"500m\"", content)
        self.assertIn("memory: \"1Gi\"", content)

    # ========================================================================
    # 6. Configuration & Secrets Separation
    # ========================================================================

    def test_configmap_and_secrets(self):
        """K8S-006: configmap.yaml and secret.yaml properly externalize settings and credentials."""
        cm_path = self.k8s_dir / "configmap.yaml"
        sec_path = self.k8s_dir / "secret.yaml"
        self.assertTrue(cm_path.exists(), "configmap.yaml is missing")
        self.assertTrue(sec_path.exists(), "secret.yaml is missing")

        cm_content = cm_path.read_text(encoding="utf-8")
        self.assertIn("kind: ConfigMap", cm_content)
        self.assertIn("name: research-config", cm_content)
        self.assertIn("APP_ENV: \"production\"", cm_content)
        self.assertIn("STORAGE_TYPE: \"s3\"", cm_content)
        self.assertIn("CHROMA_SERVER_HOST:", cm_content)

        sec_content = sec_path.read_text(encoding="utf-8")
        self.assertIn("kind: Secret", sec_content)
        self.assertIn("name: research-secrets", sec_content)
        self.assertIn("DATABASE_URL:", sec_content)
        self.assertIn("REDIS_URL:", sec_content)
        self.assertIn("JWT_SECRET_KEY:", sec_content)
        self.assertIn("LLM_API_KEY:", sec_content)

    # ========================================================================
    # 7. Ingress Routing Verification
    # ========================================================================

    def test_ingress_manifest(self):
        """K8S-007: ingress.yaml routes api.example.com and app.example.com to respective services."""
        manifest_path = self.k8s_dir / "ingress.yaml"
        self.assertTrue(manifest_path.exists(), "ingress.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")

        self.assertIn("kind: Ingress", content)
        self.assertIn("name: research-ingress", content)
        self.assertIn("ingressClassName: nginx", content)
        self.assertIn("api.example.com", content)
        self.assertIn("name: research-api", content)
        self.assertIn("number: 8000", content)
        self.assertIn("app.example.com", content)
        self.assertIn("name: research-frontend", content)
        self.assertIn("number: 80", content)

    # ========================================================================
    # 8. Horizontal Pod Autoscaler Verification
    # ========================================================================

    def test_backend_hpa_manifest(self):
        """K8S-008: backend-hpa.yaml scales research-api between 2 and 8 replicas on CPU target."""
        manifest_path = self.k8s_dir / "backend-hpa.yaml"
        self.assertTrue(manifest_path.exists(), "backend-hpa.yaml is missing")
        content = manifest_path.read_text(encoding="utf-8")

        self.assertIn("kind: HorizontalPodAutoscaler", content)
        self.assertIn("name: research-api-hpa", content)
        self.assertIn("name: research-api", content)
        self.assertIn("minReplicas: 2", content)
        self.assertIn("maxReplicas: 8", content)
        self.assertIn("averageUtilization: 70", content)

    # ========================================================================
    # 9. Architecture Documentation Verification
    # ========================================================================

    def test_kubernetes_architecture_documentation(self):
        """K8S-009: docs/infrastructure/KUBERNETES_ARCHITECTURE.md details control plane, failure runbook, and scaling."""
        doc_path = self.docs_dir / "KUBERNETES_ARCHITECTURE.md"
        self.assertTrue(doc_path.exists(), "KUBERNETES_ARCHITECTURE.md is missing")
        content = doc_path.read_text(encoding="utf-8")

        self.assertIn("Control Plane vs. Worker Nodes", content)
        self.assertIn("kube-apiserver", content)
        self.assertIn("etcd", content)
        self.assertIn("Workload Separation: API vs. Ingestion Workers", content)
        self.assertIn("Health Probes & Lifecycle Management", content)
        self.assertIn("Zero-Downtime Rolling Deployments & Rollbacks", content)
        self.assertIn("Horizontal Pod Autoscaling (HPA)", content)
        self.assertIn("Common Failure Modes & Diagnostics Runbook", content)
        self.assertIn("ImagePullBackOff", content)
        self.assertIn("CrashLoopBackOff", content)
        self.assertIn("OOMKilled", content)
        self.assertIn("When Kubernetes is Unnecessary vs. Appropriate", content)


if __name__ == "__main__":
    unittest.main()
