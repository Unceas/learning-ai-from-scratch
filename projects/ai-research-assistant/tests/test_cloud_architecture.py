"""Pytest suite for Day 179 Cloud Infrastructure & AWS Architecture."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CLOUD_DOCS = Path(PROJECT_DIR, "docs", "cloud")


def test_cloud_docs_exist():
    """Verify all 6 cloud documentation files exist and are populated."""
    required_files = [
        "AWS_ARCHITECTURE.md",
        "NETWORK_DESIGN.md",
        "IAM_SECURITY.md",
        "COST_MODEL.md",
        "DEPLOYMENT_STRATEGY.md",
        "ADR-001-aws-compute-platform.md",
    ]
    for filename in required_files:
        p = CLOUD_DOCS / filename
        assert p.exists(), f"Missing cloud documentation: {filename}"
        assert p.stat().st_size > 400, f"Cloud doc {filename} is too small"


def test_aws_architecture_well_architected():
    """Verify AWS_ARCHITECTURE.md covers Well-Architected Framework and SLOs."""
    content = (CLOUD_DOCS / "AWS_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "Operational Excellence" in content
    assert "Security" in content
    assert "Reliability" in content
    assert "Cost Optimization" in content
    assert "Amazon ECS on AWS Fargate" in content
    assert "Amazon RDS for PostgreSQL" in content
    assert "API Availability" in content


def test_network_design_subnets_and_security_groups():
    """Verify NETWORK_DESIGN.md specifies 6 subnets across 2 AZs and SG matrix."""
    content = (CLOUD_DOCS / "NETWORK_DESIGN.md").read_text(encoding="utf-8")
    assert "10.0.0.0/16" in content
    assert "10.0.1.0/24" in content
    assert "10.0.11.0/24" in content
    assert "10.0.21.0/24" in content
    assert "sg-alb" in content
    assert "sg-api" in content
    assert "sg-worker" in content
    assert "sg-rds" in content


def test_iam_security_and_adr():
    """Verify IAM_SECURITY.md and ADR-001 compute platform decision."""
    iam_content = (CLOUD_DOCS / "IAM_SECURITY.md").read_text(encoding="utf-8")
    adr_content = (CLOUD_DOCS / "ADR-001-aws-compute-platform.md").read_text(encoding="utf-8")

    assert "ECS Task Role" in iam_content
    assert "OIDC Federation" in iam_content
    assert "AWS Secrets Manager" in iam_content

    assert "Amazon ECS with AWS Fargate" in adr_content
    assert "Status" in adr_content
    assert "Accepted" in adr_content
