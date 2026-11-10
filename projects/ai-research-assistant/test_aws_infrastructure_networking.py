"""Suite #61: AWS Infrastructure Networking & Registry Implementation Tests.

Validates:
1. Public routing and Internet Gateway association.
2. NAT Gateway provisioning and private subnet routing.
3. Strict database subnet isolation (no internet/NAT route).
4. Security group chaining and least-privilege rules (ALB -> App -> DB/Redis).
5. S3 Gateway VPC Endpoint configuration and route table associations.
6. Networking module outputs exportation.
7. ECR registry immutability, vulnerability scanning, and lifecycle policies.
8. Root composition and microservice registry orchestration.
9. Multi-environment workspace outputs and documentation completeness.
"""

import os
import sys
import unittest
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)
os.chdir(PROJECT_DIR)


class TestAWSInfrastructureNetworking(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proj_dir = Path(PROJECT_DIR)
        cls.tf_dir = cls.proj_dir / "infrastructure" / "terraform"
        cls.net_dir = cls.tf_dir / "modules" / "networking"
        cls.reg_dir = cls.tf_dir / "modules" / "registry"
        cls.docs_dir = cls.proj_dir / "docs" / "infrastructure"

    # ========================================================================
    # 1. Public Routing & Internet Gateway
    # ========================================================================

    def test_public_routing_and_igw(self):
        """NET-001: Public subnets are associated with a public route table pointing to IGW."""
        main_tf = (self.net_dir / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_route_table" "public"', main_tf)
        self.assertIn('resource "aws_route" "public_internet"', main_tf)
        self.assertIn('destination_cidr_block = "0.0.0.0/0"', main_tf)
        self.assertIn("gateway_id             = aws_internet_gateway.this.id", main_tf)
        self.assertIn('resource "aws_route_table_association" "public"', main_tf)

    # ========================================================================
    # 2. NAT Gateway & Private Routing
    # ========================================================================

    def test_nat_gateway_and_private_routing(self):
        """NET-002: NAT Gateway with Elastic IP routes outbound traffic for private application subnets."""
        main_tf = (self.net_dir / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_eip" "nat"', main_tf)
        self.assertIn('domain = "vpc"', main_tf)
        self.assertIn('resource "aws_nat_gateway" "this"', main_tf)
        self.assertIn("allocation_id = aws_eip.nat.id", main_tf)
        self.assertIn("subnet_id     = aws_subnet.public[0].id", main_tf)
        self.assertIn("aws_internet_gateway.this", main_tf)

        self.assertIn('resource "aws_route_table" "private"', main_tf)
        self.assertIn('resource "aws_route" "private_nat"', main_tf)
        self.assertIn("nat_gateway_id         = aws_nat_gateway.this.id", main_tf)
        self.assertIn('resource "aws_route_table_association" "private"', main_tf)

    # ========================================================================
    # 3. Isolated Database Subnets (Zero Internet/NAT Route)
    # ========================================================================

    def test_isolated_database_subnets_routing(self):
        """NET-003: Database subnets have dedicated route tables with strictly NO default internet or NAT route."""
        main_tf = (self.net_dir / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_route_table" "database"', main_tf)
        self.assertIn('resource "aws_route_table_association" "database"', main_tf)

        # Confirm there is NO database route resource defining 0.0.0.0/0
        self.assertNotIn('resource "aws_route" "database_internet"', main_tf)
        self.assertNotIn('resource "aws_route" "database_nat"', main_tf)

    # ========================================================================
    # 4. Security Group Chaining & Least-Privilege Rules
    # ========================================================================

    def test_security_groups_least_privilege(self):
        """NET-004: Security groups enforce chained ingress; DB/Redis never accept 0.0.0.0/0."""
        main_tf = (self.net_dir / "main.tf").read_text(encoding="utf-8")

        # ALB Security Group
        self.assertIn('resource "aws_security_group" "alb"', main_tf)
        self.assertIn("from_port   = 443", main_tf)
        self.assertIn("from_port   = 80", main_tf)

        # Application Security Group
        self.assertIn('resource "aws_security_group" "application"', main_tf)
        self.assertIn("from_port       = 8000", main_tf)
        self.assertIn("security_groups = [aws_security_group.alb.id]", main_tf)

        # Database Security Group
        self.assertIn('resource "aws_security_group" "database"', main_tf)
        self.assertIn("from_port       = 5432", main_tf)
        self.assertIn("to_port         = 5432", main_tf)
        self.assertIn("security_groups = [aws_security_group.application.id]", main_tf)

        # Redis Security Group
        self.assertIn('resource "aws_security_group" "redis"', main_tf)
        self.assertIn("from_port       = 6379", main_tf)

        # Verify database section doesn't have 0.0.0.0/0 ingress
        db_start = main_tf.find('resource "aws_security_group" "database"')
        db_end = main_tf.find('resource "aws_security_group" "redis"')
        db_block = main_tf[db_start:db_end]
        ingress_part = db_block[:db_block.find("egress {")]
        self.assertNotIn("0.0.0.0/0", ingress_part, "Database ingress must never contain 0.0.0.0/0!")

    # ========================================================================
    # 5. S3 Gateway VPC Endpoint
    # ========================================================================

    def test_s3_gateway_vpc_endpoint(self):
        """NET-005: S3 Gateway endpoint routes traffic directly without NAT fees."""
        main_tf = (self.net_dir / "main.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_vpc_endpoint" "s3"', main_tf)
        self.assertIn('service_name      = "com.amazonaws.${var.aws_region}.s3"', main_tf)
        self.assertIn('vpc_endpoint_type = "Gateway"', main_tf)
        self.assertIn("aws_route_table.private[*].id", main_tf)
        self.assertIn("aws_route_table.database[*].id", main_tf)

    # ========================================================================
    # 6. Networking Module Outputs
    # ========================================================================

    def test_networking_module_outputs(self):
        """NET-006: Networking outputs export all IDs for VPC, subnets, SGs, NAT, and endpoints."""
        outs_tf = (self.net_dir / "outputs.tf").read_text(encoding="utf-8")

        expected_outputs = [
            'output "vpc_id"',
            'output "public_subnet_ids"',
            'output "private_subnet_ids"',
            'output "database_subnet_ids"',
            'output "public_route_table_id"',
            'output "private_route_table_ids"',
            'output "database_route_table_ids"',
            'output "internet_gateway_id"',
            'output "nat_gateway_id"',
            'output "nat_eip"',
            'output "s3_endpoint_id"',
            'output "alb_security_group_id"',
            'output "application_security_group_id"',
            'output "database_security_group_id"',
            'output "redis_security_group_id"',
        ]
        for out in expected_outputs:
            self.assertIn(out, outs_tf, f"Missing networking output: {out}")

    # ========================================================================
    # 7. ECR Registry Module Hardening & Lifecycle
    # ========================================================================

    def test_ecr_registry_hardening(self):
        """NET-007: ECR repository enforces immutable tags, push scanning, and rollback lifecycles."""
        main_tf = (self.reg_dir / "main.tf").read_text(encoding="utf-8")
        outs_tf = (self.reg_dir / "outputs.tf").read_text(encoding="utf-8")
        vars_tf = (self.reg_dir / "variables.tf").read_text(encoding="utf-8")

        self.assertIn('resource "aws_ecr_repository" "this"', main_tf)
        self.assertIn("image_tag_mutability = var.image_tag_mutability", main_tf)
        self.assertIn("scan_on_push = var.scan_on_push", main_tf)
        self.assertIn('encryption_type = "AES256"', main_tf)
        self.assertIn('resource "aws_ecr_lifecycle_policy" "this"', main_tf)
        self.assertIn("countType     = \"imageCountMoreThan\"", main_tf)

        self.assertIn('variable "repository_name"', vars_tf)
        self.assertIn('output "repository_url"', outs_tf)
        self.assertIn('output "repository_urls"', outs_tf)

    # ========================================================================
    # 8. Root Composition & Microservice Registry Wiring
    # ========================================================================

    def test_root_composition_wiring(self):
        """NET-008: Root main.tf connects networking, storage, and registries for api, worker, and frontend."""
        root_main = (self.tf_dir / "main.tf").read_text(encoding="utf-8")
        root_outs = (self.tf_dir / "outputs.tf").read_text(encoding="utf-8")

        self.assertIn('module "networking"', root_main)
        self.assertIn('module "document_storage"', root_main)
        self.assertIn('module "api_registry"', root_main)
        self.assertIn('module "worker_registry"', root_main)
        self.assertIn('module "frontend_registry"', root_main)

        self.assertIn('output "vpc_id"', root_outs)
        self.assertIn('output "nat_gateway_id"', root_outs)
        self.assertIn('output "s3_endpoint_id"', root_outs)
        self.assertIn('output "application_security_group_id"', root_outs)
        self.assertIn('output "database_security_group_id"', root_outs)
        self.assertIn('output "api_repository_url"', root_outs)
        self.assertIn('output "worker_repository_url"', root_outs)
        self.assertIn('output "frontend_repository_url"', root_outs)

    # ========================================================================
    # 9. Implementation Documentation
    # ========================================================================

    def test_aws_networking_implementation_doc(self):
        """NET-009: docs/infrastructure/AWS_NETWORKING_IMPLEMENTATION.md covers topology, SGs, endpoints, gaps."""
        doc_path = self.docs_dir / "AWS_NETWORKING_IMPLEMENTATION.md"
        self.assertTrue(doc_path.exists(), "AWS_NETWORKING_IMPLEMENTATION.md is missing")
        content = doc_path.read_text(encoding="utf-8")

        self.assertIn("Target Network Topology & Traffic Flow", content)
        self.assertIn("Subnet Allocation & CIDR Matrix", content)
        self.assertIn("Route Table Design & Isolation Verification", content)
        self.assertIn("Security Group Chaining Matrix", content)
        self.assertIn("S3 Gateway VPC Endpoint Architecture", content)
        self.assertIn("Container Registry (ECR) Implementation", content)
        self.assertIn("Remaining Production Deployment Gaps", content)


if __name__ == "__main__":
    unittest.main()
