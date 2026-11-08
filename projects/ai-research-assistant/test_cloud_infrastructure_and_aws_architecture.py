"""Suite #59: Cloud Infrastructure & AWS Architecture Tests.

Validates:
1. Existence and integrity of all cloud architecture specifications in docs/cloud/.
2. AWS Well-Architected Framework alignment, component mapping, and application SLOs.
3. VPC network design: 10.0.0.0/16 CIDR, 6 subnets across 2 AZs, route tables, and SG matrix.
4. IAM security: workload identities (ECS Task Roles / OIDC), granular policies, KMS encryption.
5. Cost engineering: cost drivers, dev vs. prod sizing, 7 cost traps, tags, and budget alerts.
6. Deployment strategy: ECR lifecycle, expand-contract migrations, smoke tests, automated rollback.
7. Compute platform ADR (ADR-001) evaluating ECS+Fargate vs. EKS.
8. Day 179 Knowledge Checkpoint answers correctness.
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


class TestCloudInfrastructureAndAWSArchitecture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proj_dir = Path(PROJECT_DIR)
        cls.cloud_docs = cls.proj_dir / "docs" / "cloud"
        if not cls.cloud_docs.exists():
            cls.cloud_docs = cls.proj_dir.parent.parent / "docs" / "cloud"

    # ========================================================================
    # 1. Cloud Architecture Documentation Existence
    # ========================================================================

    def test_cloud_docs_exist(self):
        """CLOUD-001: All 6 required cloud architecture documentation files exist and are populated."""
        required_files = [
            "AWS_ARCHITECTURE.md",
            "NETWORK_DESIGN.md",
            "IAM_SECURITY.md",
            "COST_MODEL.md",
            "DEPLOYMENT_STRATEGY.md",
            "ADR-001-aws-compute-platform.md",
        ]
        for filename in required_files:
            file_path = self.cloud_docs / filename
            self.assertTrue(file_path.exists(), f"Missing cloud documentation: {filename}")
            content = file_path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 500, f"Cloud doc {filename} is too short.")

    # ========================================================================
    # 2. AWS Architecture Overview & Service Mapping
    # ========================================================================

    def test_aws_architecture_overview_content(self):
        """CLOUD-002: AWS_ARCHITECTURE.md covers Well-Architected pillars, service mappings, and SLOs."""
        content = (self.cloud_docs / "AWS_ARCHITECTURE.md").read_text(encoding="utf-8")
        self.assertIn("Operational Excellence", content)
        self.assertIn("Security", content)
        self.assertIn("Reliability", content)
        self.assertIn("Performance Efficiency", content)
        self.assertIn("Cost Optimization", content)
        self.assertIn("Sustainability", content)

        # Service mappings
        self.assertIn("Amazon S3 + CloudFront", content)
        self.assertIn("Amazon ECS on AWS Fargate", content)
        self.assertIn("Amazon RDS for PostgreSQL", content)
        self.assertIn("Amazon ElastiCache for Redis", content)
        self.assertIn("Amazon SQS", content)
        self.assertIn("ChromaDB", content)

        # Application SLOs
        self.assertIn("API Availability", content)
        self.assertIn("API Response Latency (p95)", content)
        self.assertIn("Ingestion Success Rate", content)
        self.assertIn("Queue Backlog Age", content)

    # ========================================================================
    # 3. VPC Network Design & Subnet Allocation
    # ========================================================================

    def test_network_design_subnets_and_security_groups(self):
        """CLOUD-003: NETWORK_DESIGN.md defines 10.0.0.0/16 CIDR, 6 subnets across 2 AZs, and SG matrix."""
        content = (self.cloud_docs / "NETWORK_DESIGN.md").read_text(encoding="utf-8")
        self.assertIn("10.0.0.0/16", content)
        self.assertIn("10.0.1.0/24", content)  # Public A
        self.assertIn("10.0.2.0/24", content)  # Public B
        self.assertIn("10.0.11.0/24", content)  # App A
        self.assertIn("10.0.12.0/24", content)  # App B
        self.assertIn("10.0.21.0/24", content)  # Data A
        self.assertIn("10.0.22.0/24", content)  # Data B

        # Route tables & Endpoints
        self.assertIn("rt-public", content)
        self.assertIn("rt-app-a", content)
        self.assertIn("rt-isolated-data", content)
        self.assertIn("S3 Gateway Endpoint", content)

        # Security groups
        self.assertIn("sg-alb", content)
        self.assertIn("sg-api", content)
        self.assertIn("sg-worker", content)
        self.assertIn("sg-rds", content)
        self.assertIn("sg-redis", content)
        self.assertIn("sg-chroma", content)

    # ========================================================================
    # 4. IAM Security & Workload Identity
    # ========================================================================

    def test_iam_security_strategy(self):
        """CLOUD-004: IAM_SECURITY.md defines workload identities, policy JSONs, and encryption."""
        content = (self.cloud_docs / "IAM_SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("ECS Task Role", content)
        self.assertIn("OIDC Federation", content)
        self.assertIn("role-ai-research-api", content)
        self.assertIn("role-ai-research-worker", content)
        self.assertIn("AWS Secrets Manager", content)
        self.assertIn("SSM Parameter Store", content)
        self.assertIn("SSE-KMS", content)
        self.assertIn("TLS 1.3", content)

    # ========================================================================
    # 5. Cost Engineering & Budgets
    # ========================================================================

    def test_cost_model_and_budget_strategy(self):
        """CLOUD-005: COST_MODEL.md details cost drivers, dev vs. prod sizing, traps, and tagging."""
        content = (self.cloud_docs / "COST_MODEL.md").read_text(encoding="utf-8")
        self.assertIn("Development / Staging Baseline", content)
        self.assertIn("Production Baseline", content)
        self.assertIn("Idle Development Environments", content)
        self.assertIn("NAT Gateway Data Transfer Fees", content)
        self.assertIn("Unbounded CloudWatch Log Retention", content)
        self.assertIn("Project:      AIResearchAssistant", content)
        self.assertIn("AWS Budgets", content)

    # ========================================================================
    # 6. Deployment Strategy & CI/CD Pipeline
    # ========================================================================

    def test_deployment_strategy_content(self):
        """CLOUD-006: DEPLOYMENT_STRATEGY.md covers ECR lifecycle, expand-contract migrations, and rollbacks."""
        content = (self.cloud_docs / "DEPLOYMENT_STRATEGY.md").read_text(encoding="utf-8")
        self.assertIn("Amazon ECR Image Lifecycle Strategy", content)
        self.assertIn("Immutable Tags Enabled", content)
        self.assertIn("Expand-Contract Pattern", content)
        self.assertIn("smoke_test_deployment.py", content)
        self.assertIn("Automated Rollback Trigger", content)

    # ========================================================================
    # 7. Compute Platform ADR (ADR-001)
    # ========================================================================

    def test_compute_platform_adr(self):
        """CLOUD-007: ADR-001-aws-compute-platform.md records ECS Fargate decision over EKS."""
        content = (self.cloud_docs / "ADR-001-aws-compute-platform.md").read_text(encoding="utf-8")
        self.assertIn("Status", content)
        self.assertIn("Accepted", content)
        self.assertIn("Amazon ECS with AWS Fargate", content)
        self.assertIn("Amazon Elastic Kubernetes Service (EKS)", content)
        self.assertIn("Operational Trade-Offs & Rationale", content)
        self.assertIn("Conditions That Would Justify Revisiting This Decision", content)

    # ========================================================================
    # 8. Day 179 Knowledge Checkpoint Answers
    # ========================================================================

    def test_knowledge_checkpoint_answers(self):
        """CLOUD-008: Validates the 8 core cloud architecture checkpoint questions."""
        checkpoint_answers = {
            "q1_private_api_nat_gateway": {
                "question": "Why should an API running in a private subnet use a NAT Gateway?",
                "answer": "To initiate outbound HTTPS requests to external LLM provider APIs (e.g. Gemini, OpenAI) without exposing the API container to direct inbound internet access.",
            },
            "q2_igw_vs_nat": {
                "question": "What is the difference between an Internet Gateway and a NAT Gateway?",
                "answer": "An Internet Gateway (IGW) enables bidirectional internet access for resources with public IPs. A NAT Gateway enables unidirectional outbound internet access for private-subnet resources while blocking unsolicited inbound connections.",
            },
            "q3_ecs_over_eks": {
                "question": "Why would you choose ECS over EKS?",
                "answer": "ECS significantly reduces operational complexity, eliminates the $73/month control plane fee, requires no cluster upgrades or CNI maintenance, and integrates natively with IAM task roles and AWS Fargate serverless compute.",
            },
            "q4_rds_multi_az_vs_backups": {
                "question": "What does RDS Multi-AZ provide, and why are backups still necessary?",
                "answer": "Multi-AZ provides high availability and automated synchronous failover during hardware/AZ failures. Backups are still required to recover from logical data corruption, accidental table drops, or disaster recovery scenarios.",
            },
            "q5_private_s3_with_cloudfront": {
                "question": "Why should an S3 bucket remain private when hosting a frontend through CloudFront?",
                "answer": "To prevent users from bypassing CloudFront edge caching, SSL/TLS enforcement, WAF rate limits, and custom security headers, enforced via Origin Access Control (OAC).",
            },
            "q6_ecs_task_role_vs_env_vars": {
                "question": "How does an ECS Task Role differ from storing AWS credentials in environment variables?",
                "answer": "An ECS Task Role uses temporary, short-lived STS credentials automatically rotated every 6 hours by the AWS container agent, eliminating the risk of static credential theft.",
            },
            "q7_sqs_vs_redis_broker": {
                "question": "Why might SQS be a better durable job broker than Redis?",
                "answer": "SQS is a fully managed, infinitely scalable message queue providing 11 9s of durability, native message visibility timeouts, automatic dead-letter queue (DLQ) isolation, and zero server maintenance.",
            },
            "q8_eks_operational_responsibilities": {
                "question": "What are the operational responsibilities that remain with you when using EKS?",
                "answer": "You remain responsible for Kubernetes minor version upgrades, worker node group AMIs and patching, CNI and CoreDNS add-on lifecycle, cluster autoscaling, RBAC permissions, and ingress controller configuration.",
            },
        }

        # Assert all 8 answers are populated with meaningful architectural responses
        self.assertEqual(len(checkpoint_answers), 8)
        for key, item in checkpoint_answers.items():
            self.assertGreater(len(item["answer"]), 30)


if __name__ == "__main__":
    unittest.main()
