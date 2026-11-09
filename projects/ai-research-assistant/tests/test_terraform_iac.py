"""Pytest suite for Day 180 Infrastructure as Code with Terraform."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TF_DIR = Path(PROJECT_DIR, "infrastructure", "terraform")
DOCS_DIR = Path(PROJECT_DIR, "docs", "infrastructure")
WORKFLOW_FILE = Path(PROJECT_DIR, ".github", "workflows", "terraform.yml")


def test_terraform_root_manifests():
    """Verify all root Terraform files exist and have content."""
    required_files = [
        "versions.tf",
        "providers.tf",
        "variables.tf",
        "locals.tf",
        "main.tf",
        "outputs.tf",
        "backend.tf",
        "terraform.tfvars.example",
        ".gitignore",
    ]
    for filename in required_files:
        p = TF_DIR / filename
        assert p.exists(), f"Missing Terraform root file: {filename}"
        assert p.stat().st_size > 10, f"Terraform file {filename} is unexpectedly empty"


def test_provider_and_versions_spec():
    """Verify Terraform >= 1.6.0, AWS provider ~> 6.0, and standard default tags."""
    versions = (TF_DIR / "versions.tf").read_text(encoding="utf-8")
    assert "required_version = \">= 1.6.0\"" in versions
    assert "source  = \"hashicorp/aws\"" in versions
    assert "version = \"~> 6.0\"" in versions

    providers = (TF_DIR / "providers.tf").read_text(encoding="utf-8")
    assert "provider \"aws\"" in providers
    assert "region = var.aws_region" in providers
    assert "Project     = \"AIResearchAssistant\"" in providers
    assert "ManagedBy   = \"Terraform\"" in providers


def test_storage_module_security_defaults():
    """Verify storage module enforces public access blocks, AES-256 encryption, and versioning."""
    storage_main = (TF_DIR / "modules" / "storage" / "main.tf").read_text(encoding="utf-8")
    assert "resource \"aws_s3_bucket\" \"this\"" in storage_main
    assert "resource \"aws_s3_bucket_public_access_block\" \"this\"" in storage_main
    assert "block_public_acls       = true" in storage_main
    assert "block_public_policy     = true" in storage_main
    assert "ignore_public_acls      = true" in storage_main
    assert "restrict_public_buckets = true" in storage_main
    assert "resource \"aws_s3_bucket_versioning\" \"this\"" in storage_main
    assert "resource \"aws_s3_bucket_server_side_encryption_configuration\" \"this\"" in storage_main
    assert "sse_algorithm = \"AES256\"" in storage_main


def test_networking_module_three_tier():
    """Verify networking module configures VPC, IGW, and public/private/database subnets."""
    net_main = (TF_DIR / "modules" / "networking" / "main.tf").read_text(encoding="utf-8")
    assert "resource \"aws_vpc\" \"this\"" in net_main
    assert "resource \"aws_internet_gateway\" \"this\"" in net_main
    assert "resource \"aws_subnet\" \"public\"" in net_main
    assert "resource \"aws_subnet\" \"private\"" in net_main
    assert "resource \"aws_subnet\" \"database\"" in net_main
    assert "resource \"aws_route_table\" \"public\"" in net_main
    assert "resource \"aws_route_table_association\" \"public\"" in net_main


def test_registry_module_lifecycle_and_immutability():
    """Verify registry module creates ECR repos with immutable image tags and lifecycle policies."""
    reg_main = (TF_DIR / "modules" / "registry" / "main.tf").read_text(encoding="utf-8")
    assert "resource \"aws_ecr_repository\" \"this\"" in reg_main
    assert "image_tag_mutability = var.image_tag_mutability" in reg_main
    assert "resource \"aws_ecr_lifecycle_policy\" \"this\"" in reg_main


def test_environments_dev_and_prod_isolation():
    """Verify dev and prod environments have isolated state keys and specific tfvars."""
    dev_main = (TF_DIR / "environments" / "dev" / "main.tf").read_text(encoding="utf-8")
    prod_main = (TF_DIR / "environments" / "prod" / "main.tf").read_text(encoding="utf-8")

    assert "key          = \"ai-research-assistant/dev/terraform.tfstate\"" in dev_main
    assert "key          = \"ai-research-assistant/prod/terraform.tfstate\"" in prod_main

    dev_tfvars = (TF_DIR / "environments" / "dev" / "terraform.tfvars").read_text(encoding="utf-8")
    prod_tfvars = (TF_DIR / "environments" / "prod" / "terraform.tfvars").read_text(encoding="utf-8")

    assert "ai-research-assistant-dev-documents-unique" in dev_tfvars
    assert "ai-research-assistant-prod-documents-unique" in prod_tfvars
    assert 'Environment = "dev"' in dev_main
    assert 'Environment = "prod"' in prod_main


def test_github_actions_terraform_workflow():
    """Verify GitHub Actions CI workflow runs fmt, init, and validate."""
    assert WORKFLOW_FILE.exists(), "Workflow file does not exist"
    content = WORKFLOW_FILE.read_text(encoding="utf-8")
    assert "hashicorp/setup-terraform" in content
    assert "terraform fmt -check -recursive" in content
    assert "terraform init -backend=false" in content
    assert "terraform validate" in content


def test_terraform_guide_and_checkpoints():
    """Verify documentation covers core concepts and all 10 Knowledge Checkpoints."""
    guide_file = DOCS_DIR / "TERRAFORM_GUIDE.md"
    assert guide_file.exists(), "TERRAFORM_GUIDE.md is missing"
    content = guide_file.read_text(encoding="utf-8")

    assert "Declarative Reproducibility" in content
    assert "Remote State Backend" in content
    assert "Drift Detection & Reconciliation" in content

    checkpoint_questions = [
        "What problem does Terraform solve compared with manually creating AWS resources?",
        "What is the difference between a Terraform resource and a data source?",
        "Why is Terraform state necessary?",
        "Why should remote state be protected and locked?",
        "What happens when someone manually changes an AWS resource managed by Terraform?",
        "Why are Terraform modules useful?",
        "Why should development and production use separate state?",
        "Why should terraform plan be reviewed before terraform apply?",
        "Why should the state bucket be bootstrapped separately?",
        "Why is Terraform validation different from actually deploying infrastructure?",
    ]
    for q in checkpoint_questions:
        assert q in content, f"Missing question in TERRAFORM_GUIDE.md: {q}"
