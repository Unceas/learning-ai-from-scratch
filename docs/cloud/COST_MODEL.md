# Cloud Cost Engineering & Budget Model

## 1. Cost Drivers & Sizing Model

Cloud cost efficiency is evaluated across seven core resource dimensions:

```text
Total Monthly Cost = Compute (ECS/Fargate) + Database (RDS) + Cache (ElastiCache) 
                     + Storage (S3/EBS) + Networking (NAT/ALB/Data Transfer) 
                     + Observability (CloudWatch) + External AI (LLM Provider Tokens)
```

### Development vs. Production Resource Profiles

| Resource Category | Development / Staging Baseline | Production Baseline (Initial Scale) | Production Scaling Ceiling (High Load) |
|---|---|---|---|
| **API Compute (FastAPI)** | 1 Fargate task (0.25 vCPU, 0.5 GB RAM) | 2 Fargate tasks (0.5 vCPU, 1 GB RAM) | 8 Fargate tasks (1.0 vCPU, 2 GB RAM) |
| **Worker Compute** | 1 Fargate task (0.5 vCPU, 1 GB RAM) | 2 Fargate tasks (1.0 vCPU, 2 GB RAM) | 6 Fargate tasks (2.0 vCPU, 4 GB RAM) |
| **Database (RDS)** | `db.t4g.micro` (Single-AZ, 20GB SSD) | `db.t4g.medium` (Multi-AZ, 100GB gp3) | `db.r6g.large` (Multi-AZ, 250GB gp3) |
| **Cache (ElastiCache)** | `cache.t4g.micro` (Single node) | `cache.t4g.small` (Multi-AZ, 1 replica) | `cache.m6g.large` (Cluster mode, 2 replicas) |
| **Networking** | 1 NAT Gateway, 1 ALB | 2 NAT Gateways, 1 ALB | 2 NAT Gateways, 1 ALB + WAF |
| **Document Storage (S3)** | 10 GB Standard | 100 GB Standard + Intelligent-Tiering | 1 TB Intelligent-Tiering + Glacier |
| **Vector DB (ChromaDB)** | Shared EBS volume (20 GB) | Persistent EBS gp3 volume (100 GB, 3000 IOPS) | Dedicated Aurora PostgreSQL pgvector instance |

---

## 2. Monthly Cost Estimation

*Estimates based on US East (N. Virginia, us-east-1) pricing.*

| AWS Service | Development Environment / Month | Production Environment / Month |
|---|---|---|
| **ECS Fargate (API & Workers)** | \$18.00 (1 API + 1 Worker, 8hr/day) | \$72.00 (4 tasks total, 24/7) |
| **Amazon RDS PostgreSQL** | \$14.00 (`db.t4g.micro`, Single-AZ) | \$98.00 (`db.t4g.medium`, Multi-AZ) |
| **Amazon ElastiCache Redis** | \$12.00 (`cache.t4g.micro`) | \$48.00 (`cache.t4g.small`, Multi-AZ) |
| **Application Load Balancer** | \$18.00 (1 ALB) | \$24.00 (1 ALB + LCU processing) |
| **NAT Gateways** | \$32.00 (1 NAT, shared hours) | \$65.00 (2 NATs, Multi-AZ) |
| **Amazon S3 & CloudFront** | \$1.00 | \$5.00 (Storage + CDN requests) |
| **CloudWatch Logs & Metrics** | \$3.00 | \$15.00 (Detailed monitoring, 30-day retention) |
| **Secrets Manager & Route 53** | \$1.50 | \$3.00 |
| **Estimated Infrastructure Total** | **~\$99.50 / month** | **~\$330.00 / month** |
| *External LLM API (Estimated)* | *\$10.00 - \$25.00 / month* | *\$50.00 - \$250.00 / month (usage-based)* |

---

## 3. Seven Cost Traps & Architectural Mitigations

| # | Common Cloud Cost Trap | Root Cause | Architectural Mitigation Applied |
|---|---|---|---|
| **1** | **Idle Development Environments** | Dev clusters and NAT gateways running 24/7 over weekends. | Automated AWS EventBridge schedules that stop staging/dev ECS tasks and RDS instances outside business hours. |
| **2** | **NAT Gateway Data Transfer Fees** | S3 document uploads and container image pulls routed through NAT at \$0.045/GB. | Enabled **S3 Gateway VPC Endpoint** (free) and PrivateLink endpoints for ECR to bypass NAT entirely. |
| **3** | **Unbounded CloudWatch Log Retention** | Application logs retained indefinitely in CloudWatch. | Enforced **14-day retention policy** on development log groups and **30-day retention** on production log groups with S3 Glacier archiving. |
| **4** | **Database Overprovisioning** | Provisioning large memory instances prematurely. | Started with right-sized `db.t4g.medium` Graviton instances; monitor connection pool efficiency before vertical scaling. |
| **5** | **Cross-AZ Data Transfer** | API tasks in AZ-A querying ElastiCache or RDS in AZ-B. | Configured target group AZ affinity to keep request flows within the same Availability Zone. |
| **6** | **Unpruned Container Registries** | Storing hundreds of intermediate CI/CD Docker image builds in ECR. | Configured **ECR Lifecycle Policy** to retain only the last 10 tagged release images and untagged images older than 7 days. |
| **7** | **Runaway LLM Provider Quotas** | Infinite retry loops or unbounded document chunk generation. | Enforced strict `max_retries=3`, request timeouts (45s), chunk token limits (1000 chars), and Redis retrieval caching. |

---

## 4. Cost Allocation Tags & Budget Alerts

### Mandatory Resource Tags
Every provisioned AWS resource must include standardized metadata:
```text
Project:      AIResearchAssistant
Environment:  Production | Staging | Development
Owner:        Engineering
ManagedBy:    Terraform
CostCenter:   RND-AI-101
```

### AWS Budgets & Alerts
- **Monthly Fixed Budget Alert**: Configured in AWS Budgets at **\$400/month** for production.
- **Velocity Warning**: Alert triggered if forecasted spend exceeds **80%** of budget before the 20th day of the billing cycle.
- **Billing Alarm**: SNS topic routes alerts directly to Slack `#devops-alerts` and email.
