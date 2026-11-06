# Kubernetes Deployment Manifests

This directory contains the production-grade declarative Kubernetes manifests for the **AI Research Assistant**.

---

## 1. Directory Structure

```text
k8s/
├── namespace.yaml             # Dedicated namespace (research-assistant)
├── configmap.yaml             # Non-sensitive application configuration
├── secret.yaml                # Sensitive credentials template (Opaque Secret)
├── backend-deployment.yaml    # Stateless FastAPI application (2 replicas, rolling updates)
├── backend-service.yaml       # Stable ClusterIP service for API pods (port 8000)
├── frontend-deployment.yaml   # React + Nginx static asset deployment (2 replicas)
├── frontend-service.yaml      # Stable ClusterIP service for Frontend pods (port 80)
├── worker-deployment.yaml     # Background ingestion & outbox dispatcher workers
├── ingress.yaml               # Nginx Ingress routing (api.example.com & app.example.com)
├── backend-hpa.yaml           # Horizontal Pod Autoscaler (2-8 replicas based on CPU/Memory)
└── README.md                  # Operational guide and runbook
```

---

## 2. Quickstart with Minikube

### Prerequisites
- [Minikube](https://minikube.sigs.k8s.io/) installed and running.
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed.

### 1. Start Cluster and Enable Ingress
```bash
minikube start --cpus=4 --memory=8192
minikube addons enable ingress
minikube addons enable metrics-server
```

### 2. Build Images in Minikube's Docker Environment
```bash
# Point local shell to Minikube's Docker daemon
eval $(minikube docker-env)

# Build backend and frontend images
docker build -t research-api:1.0.0 -f backend/Dockerfile .
docker build -t research-frontend:1.0.0 -f frontend/Dockerfile ./frontend
```

### 3. Deploy All Manifests
```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Apply config and secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. Deploy applications, services, and ingress
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/backend-hpa.yaml
```

---

## 3. Operational Commands & Runbook

### Inspecting Cluster Status
```bash
# Get all workloads in the namespace
kubectl get all -n research-assistant

# View rollout status
kubectl rollout status deployment/research-api -n research-assistant

# View pod logs
kubectl logs -l app=research-api -n research-assistant --tail=100 -f
kubectl logs -l app=document-worker -n research-assistant --tail=100 -f

# Check HPA status
kubectl get hpa -n research-assistant
```

### Rolling Update & Rollback
```bash
# Update backend image version
kubectl set image deployment/research-api api=research-api:1.0.1 -n research-assistant

# Monitor the rolling deployment
kubectl rollout status deployment/research-api -n research-assistant

# View revision history
kubectl rollout history deployment/research-api -n research-assistant

# Roll back to the previous deployment revision
kubectl rollout undo deployment/research-api -n research-assistant
```

---

## 4. Common Troubleshooting Scenarios

| Issue | Diagnostic Command | Typical Solution |
|---|---|---|
| `ImagePullBackOff` | `kubectl describe pod <pod> -n research-assistant` | Image tag not found or missing container registry pull secret. |
| `CrashLoopBackOff` | `kubectl logs <pod> -n research-assistant --previous` | Missing required secret/config environment variable or unhandled startup exception. |
| `Readiness Probe Failed` | `kubectl describe pod <pod> -n research-assistant` | Database/Redis unreachable or `/health/ready` returning 503. |
| `OOMKilled` | `kubectl describe pod <pod> -n research-assistant` | Increase `resources.limits.memory` for worker or API pods. |
| No Ingress Traffic | `kubectl describe ingress research-ingress -n research-assistant` | Ingress controller not enabled or host header mismatch. |
