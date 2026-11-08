# ADR-001: AWS Compute Platform Selection — Amazon ECS with AWS Fargate vs. Amazon EKS

## Status
Accepted

## Context
The AI Research Assistant requires a secure, scalable, and maintainable compute runtime in AWS. In Day 178, we constructed declarative Kubernetes manifests (`k8s/`) establishing container orchestration foundations. We must now decide whether to deploy the production application on **Amazon Elastic Kubernetes Service (EKS)** or **Amazon Elastic Container Service (ECS) with AWS Fargate**.

The application consists of two distinct workload profiles:
1. **FastAPI Web Application**: Latency-sensitive, I/O-bound, stateless HTTP service.
2. **Background Ingestion Workers**: CPU-intensive (PDF parsing), memory-heavy (embedding generation), and asynchronous batch processing.

Both workloads interact with managed AWS backends: Amazon RDS (PostgreSQL), Amazon ElastiCache (Redis), Amazon S3, and external LLM APIs.

---

## Decision

We select **Amazon ECS with AWS Fargate** as the primary production compute platform, while retaining our versioned Kubernetes manifests (`k8s/`) for enterprise multi-cloud portability and local Minikube development.

---

## Alternatives Considered

### 1. Amazon Elastic Kubernetes Service (EKS)
- **Description**: Fully managed Kubernetes control plane with EC2 Managed Node Groups or Karpenter.
- **Why Deferred**:
  - Requires maintaining control-plane upgrades, CNI plugins (AWS VPC CNI), CoreDNS, Kube-Proxy, and node group AMIs.
  - Incurs a fixed **\$73.00/month control plane fee** per cluster, regardless of utilization.
  - Adds significant operational overhead (Helm, RBAC, admission controllers, cert-manager) for a team that does not have dedicated 24/7 Platform/SRE staffing.

### 2. AWS App Runner
- **Description**: Fully managed web application platform that builds and runs containers directly.
- **Why Rejected**:
  - Lacks native support for complex multi-container topologies requiring decoupled background workers, internal private networking, and custom autoscaling signals (e.g. SQS queue depth).

### 3. Raw EC2 Instances with Docker Compose
- **Description**: Running Docker Compose directly on provisioned EC2 virtual machines.
- **Why Rejected**:
  - Introduces single-point-of-failure vulnerabilities, manual OS patching, lack of automated task self-healing, and crude autoscaling.

---

## Operational Trade-Offs & Rationale

| Evaluation Criterion | Amazon ECS + AWS Fargate (Chosen) | Amazon EKS (Alternative) |
|---|---|---|
| **Operational Overhead** | **Low**: Zero cluster management, no EC2 patching, no K8s version upgrade toil. | **High**: Requires ongoing control plane maintenance, node group upgrades, and add-on patching. |
| **Fixed Cost Overhead** | **\$0.00 / month**: Pay strictly for vCPU and memory allocated to running tasks. | **\$73.00 / month**: Fixed cost for the EKS control plane plus node infrastructure. |
| **IAM Integration** | **Native**: Granular IAM roles assigned directly at the ECS Task level (`taskRoleArn`). | **Complex**: Requires OIDC provider configuration, IAM Roles for Service Accounts (IRSA), or EKS Pod Identity agent. |
| **Autoscaling Mechanics** | **Simple**: Native Application Auto Scaling based on CPU/Memory and SQS queue depth. | **Powerful but Complex**: Requires Metrics Server, HPA, KEDA, and cluster autoscalers (Karpenter). |
| **Worker Separation** | **Native**: Separate ECS task definitions and services sharing the same ECR image. | **Native**: Separate Deployments within the same namespace. |

---

## Migration & Architectural Implications

1. **Dual-Stack Portability**: Because our codebase is completely containerized (`backend/Dockerfile`, `frontend/Dockerfile`), running on ECS requires only ECS Task Definitions (`task-definition.json`), with zero changes to application code.
2. **Kubernetes Artifact Preservation**: The `k8s/` manifests created on Day 178 remain fully functional for local development, Minikube testing, and enterprise customers requiring deployment into existing on-premise Kubernetes clusters.

---

## Conditions That Would Justify Revisiting This Decision

We will re-evaluate migrating to Amazon EKS when one or more of the following triggers occur:
1. **GPU Acceleration Requirements**: If document embedding and cross-encoder reranking transition from CPU to dedicated GPU instances (e.g. NVIDIA A10G / G5 instances) requiring fine-grained GPU sharing (MIG) or custom Kubernetes schedulers.
2. **Service Mesh & Advanced Traffic Management**: If inter-service communication requires mutual TLS (mTLS), distributed canary deployments, or complex traffic shaping provided by Istio or Linkerd.
3. **Enterprise Organization Mandate**: If our parent engineering organization standardizes on a centralized, multi-tenant Kubernetes platform managed by a dedicated Platform Engineering team.
