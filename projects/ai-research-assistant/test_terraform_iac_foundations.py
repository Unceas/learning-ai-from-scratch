"""Suite #60: Infrastructure as Code with Terraform Tests.

Validates:
1. Root Terraform configuration files (versions, providers, variables, locals, main, outputs, backend, .gitignore).
2. AWS provider version constraints (>= 1.6.0, hashicorp/aws ~> 6.0) and default tags.
3. Storage module: S3 bucket, versioning, AES-256 encryption, public access block.
4. Networking module: 3-tier VPC, IGW, public/private/database subnets, route tables.
5. Registry module: ECR repositories, immutable tags, lifecycle policies.
6. Environment separation: dev vs. prod workspaces with distinct state keys.
7. GitHub Actions Terraform validation workflow (.github/workflows/terraform.yml).
8. Architecture documentation (docs/infrastructure/TERRAFORM_GUIDE.md).
9. Programmatic validation of Day 180 Knowledge Checkpoint questions.
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


class TestTerraformIaCFoundations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proj_dir = Path(PROJECT_DIR)
        cls.tf_dir = cls.proj_dir / "infrastructure" / "terraform"
        cls.docs_dir = cls.proj_dir / "docs" / "infrastructure"
        cls.github_dir = cls.proj_dir / ".github" / "workflows"

    # ========================================================================
    # 1. Root Configuration Files Existence
    # ========================================================================

    def test_root_terraform_files_exist(self):
        """TF-001: Root Terraform directory contains all foundational HCL files."""
        expected_files = [
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
        for filename in expected_files:
            file_path = self.tf_dir / filename
            self.assertTrue(file_path.exists(), f"Missing root Terraform file: {filename}")
            content = file_path.read_text(encoding="utf-8")
            self.assertGreater(len(content), 10, f"File {filename} is empty")

    # ========================================================================
    # 2. Provider & Version Constraints
    # ========================================================================

    def test_provider_and_versions(self):
        """TF-002: versions.tf and providers.tf define valid AWS provider constraints and default tags."""
        versions = (self.tf_dir / "versions.tf").read_text(encoding="utf-8")
        self.assertIn("required_version = \">= 1.6.0\"", versions)
        self.assertIn("source  = \"hashicorp/aws\"", versions)
        self.assertIn("version = \"~> 6.0\"", versions)

        providers = (self.tf_dir / "providers.tf").read_text(encoding="utf-8")
        self.assertIn("provider \"aws\"", providers)
        self.assertIn("region = var.aws_region", providers)
        self.assertIn("Project     = \"AIResearchAssistant\"", providers)
        self.assertIn("ManagedBy   = \"Terraform\"", providers)

    # ========================================================================
    # 3. Storage Module Verification
    # ========================================================================

    def test_storage_module_manifests(self):
        """TF-003: modules/storage/ defines S3 bucket with encryption, versioning, and public access blocks."""
        mod_dir = self.tf_dir / "modules" / "storage"
        main_tf = (mod_dir / "main.tf").read_text(encoding="utf-8")
        vars_tf = (mod_dir / "variables.tf").read_text(encoding="utf-8")
        outs_tf = (mod_dir / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn("resource \"aws_s3_bucket\" \"this\"", main_tf)
        self.assertIn("resource \"aws_s3_bucket_public_access_block\" \"this\"", main_tf)
        self.assertIn("block_public_acls       = true", main_tf)
        self.assertIn("restrict_public_buckets = true", main_tf)
        self.assertIn("resource \"aws_s3_bucket_versioning\" \"this\"", main_tf)
        self.assertIn("resource \"aws_s3_bucket_server_side_encryption_configuration\" \"this\"", main_tf)
        self.assertIn("sse_algorithm = \"AES256\"", main_tf)

        self.assertIn("variable \"bucket_name\"", vars_tf)
        self.assertIn("output \"bucket_name\"", outs_tf)
        self.assertIn("output \"bucket_arn\"", outs_tf)

    # ========================================================================
    # 4. Networking Module Verification
    # ========================================================================

    def test_networking_module_manifests(self):
        """TF-004: modules/networking/ defines 3-tier VPC, subnets across AZs, and route tables."""
        mod_dir = self.tf_dir / "modules" / "networking"
        main_tf = (mod_dir / "main.tf").read_text(encoding="utf-8")
        vars_tf = (mod_dir / "variables.tf").read_text(encoding="utf-8")
        outs_tf = (mod_dir / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn("resource \"aws_vpc\" \"this\"", main_tf)
        self.assertIn("resource \"aws_internet_gateway\" \"this\"", main_tf)
        self.assertIn("resource \"aws_subnet\" \"public\"", main_tf)
        self.assertIn("resource \"aws_subnet\" \"private\"", main_tf)
        self.assertIn("resource \"aws_subnet\" \"database\"", main_tf)
        self.assertIn("resource \"aws_route_table\" \"public\"", main_tf)
        self.assertIn("resource \"aws_route_table_association\" \"public\"", main_tf)

        self.assertIn("variable \"vpc_cidr\"", vars_tf)
        self.assertIn("output \"vpc_id\"", outs_tf)
        self.assertIn("output \"public_subnet_ids\"", outs_tf)
        self.assertIn("output \"private_subnet_ids\"", outs_tf)
        self.assertIn("output \"database_subnet_ids\"", outs_tf)

    # ========================================================================
    # 5. Registry Module Verification
    # ========================================================================

    def test_registry_module_manifests(self):
        """TF-005: modules/registry/ defines ECR repositories with immutability and lifecycle rules."""
        mod_dir = self.tf_dir / "modules" / "registry"
        main_tf = (mod_dir / "main.tf").read_text(encoding="utf-8")
        outs_tf = (mod_dir / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn("resource \"aws_ecr_repository\" \"this\"", main_tf)
        self.assertIn("image_tag_mutability = var.image_tag_mutability", main_tf)
        self.assertIn("resource \"aws_ecr_lifecycle_policy\" \"this\"", main_tf)
        self.assertIn("output \"repository_urls\"", outs_tf)
        self.assertIn("output \"repository_arns\"", outs_tf)

    # ========================================================================
    # 6. Environment Separation Verification
    # ========================================================================

    def test_environment_isolation_and_state_keys(self):
        """TF-006: environments/dev and environments/prod use separate state keys and variables."""
        dev_main = (self.tf_dir / "environments" / "dev" / "main.tf").read_text(encoding="utf-8")
        prod_main = (self.tf_dir / "environments" / "prod" / "main.tf").read_text(encoding="utf-8")

        # Distinct state keys
        self.assertIn("key          = \"ai-research-assistant/dev/terraform.tfstate\"", dev_main)
        self.assertIn("key          = \"ai-research-assistant/prod/terraform.tfstate\"", prod_main)

        # Module references
        self.assertIn("module \"dev_infrastructure\"", dev_main)
        self.assertIn("module \"prod_infrastructure\"", prod_main)

        # tfvars existence
        dev_vars = (self.tf_dir / "environments" / "dev" / "terraform.tfvars").read_text(encoding="utf-8")
        prod_vars = (self.tf_dir / "environments" / "prod" / "terraform.tfvars").read_text(encoding="utf-8")
        self.assertIn("documents_bucket_name", dev_vars)
        self.assertIn("documents_bucket_name", prod_vars)

    # ========================================================================
    # 7. GitHub Actions Workflow Verification
    # ========================================================================

    def test_github_actions_workflow(self):
        """TF-007: .github/workflows/terraform.yml defines format check, init, and validate steps."""
        wf_file = self.github_dir / "terraform.yml"
        self.assertTrue(wf_file.exists(), "terraform.yml workflow is missing")
        content = wf_file.read_text(encoding="utf-8")

        self.assertIn("hashicorp/setup-terraform", content)
        self.assertIn("terraform fmt -check -recursive", content)
        self.assertIn("terraform init -backend=false", content)
        self.assertIn("terraform validate", content)

    # ========================================================================
    # 8. Documentation Verification
    # ========================================================================

    def test_terraform_guide_documentation(self):
        """TF-008: docs/infrastructure/TERRAFORM_GUIDE.md covers lifecycle, state, drift, and checkpoint."""
        guide_file = self.docs_dir / "TERRAFORM_GUIDE.md"
        self.assertTrue(guide_file.exists(), "TERRAFORM_GUIDE.md is missing")
        content = guide_file.read_text(encoding="utf-8")

        self.assertIn("Declarative Reproducibility", content)
        self.assertIn("terraform init", content)
        self.assertIn("terraform fmt", content)
        self.assertIn("terraform validate", content)
        self.assertIn("terraform plan", content)
        self.assertIn("terraform apply", content)
        self.assertIn("Remote State Backend", content)
        self.assertIn("Drift Detection & Reconciliation", content)
        self.assertIn("Knowledge Checkpoint", content)

    # ========================================================================
    # 9. Knowledge Checkpoint Questions Assertion
    # ========================================================================

    def test_knowledge_checkpoint_answers(self):
        """TF-009: Asserts the 10 Knowledge Checkpoint concepts are covered."""
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
        content = (self.docs_dir / "TERRAFORM_GUIDE.md").read_text(encoding="utf-8")
        for q in checkpoint_questions:
            self.assertIn(q, content, f"Missing question in TERRAFORM_GUIDE.md: {q}")


if __name__ == "__main__":
    unittest.main()
