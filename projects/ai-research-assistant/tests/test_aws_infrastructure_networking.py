"""Pytest suite for Day 181 AWS Infrastructure & Networking Implementation."""

import os
from pathlib import Path

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TF_DIR = Path(PROJECT_DIR, "infrastructure", "terraform")
NET_DIR = TF_DIR / "modules" / "networking"
REG_DIR = TF_DIR / "modules" / "registry"
DOCS_DIR = Path(PROJECT_DIR, "docs", "infrastructure")


def test_public_routing_and_internet_gateway():
    """Verify public route table is bound to IGW and public subnets."""
    main_tf = (NET_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_route_table" "public"' in main_tf
    assert 'resource "aws_route" "public_internet"' in main_tf
    assert 'destination_cidr_block = "0.0.0.0/0"' in main_tf
    assert "gateway_id             = aws_internet_gateway.this.id" in main_tf
    assert 'resource "aws_route_table_association" "public"' in main_tf


def test_nat_gateway_and_private_routing():
    """Verify NAT Gateway with Elastic IP routes private subnet outbound traffic."""
    main_tf = (NET_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_eip" "nat"' in main_tf
    assert 'domain = "vpc"' in main_tf
    assert 'resource "aws_nat_gateway" "this"' in main_tf
    assert "allocation_id = aws_eip.nat.id" in main_tf
    assert "subnet_id     = aws_subnet.public[0].id" in main_tf
    assert 'resource "aws_route_table" "private"' in main_tf
    assert 'resource "aws_route" "private_nat"' in main_tf
    assert "nat_gateway_id         = aws_nat_gateway.this.id" in main_tf
    assert 'resource "aws_route_table_association" "private"' in main_tf


def test_isolated_database_subnets():
    """Verify database subnets have route tables with strictly no 0.0.0.0/0 route."""
    main_tf = (NET_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_route_table" "database"' in main_tf
    assert 'resource "aws_route_table_association" "database"' in main_tf
    assert 'resource "aws_route" "database_internet"' not in main_tf
    assert 'resource "aws_route" "database_nat"' not in main_tf


def test_security_group_chaining():
    """Verify security group chaining (ALB -> App -> DB/Redis) with no public DB ingress."""
    main_tf = (NET_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_security_group" "alb"' in main_tf
    assert 'resource "aws_security_group" "application"' in main_tf
    assert 'resource "aws_security_group" "database"' in main_tf
    assert 'resource "aws_security_group" "redis"' in main_tf

    assert "security_groups = [aws_security_group.alb.id]" in main_tf
    assert "security_groups = [aws_security_group.application.id]" in main_tf

    # Verify no 0.0.0.0/0 ingress in database
    db_idx = main_tf.find('resource "aws_security_group" "database"')
    redis_idx = main_tf.find('resource "aws_security_group" "redis"')
    db_block = main_tf[db_idx:redis_idx]
    ingress_block = db_block[:db_block.find("egress {")]
    assert "0.0.0.0/0" not in ingress_block


def test_s3_gateway_vpc_endpoint():
    """Verify S3 Gateway Endpoint is associated with private and database route tables."""
    main_tf = (NET_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_vpc_endpoint" "s3"' in main_tf
    assert 'vpc_endpoint_type = "Gateway"' in main_tf
    assert "aws_route_table.private[*].id" in main_tf
    assert "aws_route_table.database[*].id" in main_tf


def test_networking_outputs():
    """Verify networking outputs export VPC, subnets, SGs, NAT, and S3 endpoint."""
    outs_tf = (NET_DIR / "outputs.tf").read_text(encoding="utf-8")
    for out in [
        "vpc_id",
        "public_subnet_ids",
        "private_subnet_ids",
        "database_subnet_ids",
        "nat_gateway_id",
        "nat_eip",
        "s3_endpoint_id",
        "alb_security_group_id",
        "application_security_group_id",
        "database_security_group_id",
    ]:
        assert f'output "{out}"' in outs_tf


def test_ecr_registry_hardening():
    """Verify ECR registry enforces immutable tags, vulnerability scanning, and lifecycle rules."""
    main_tf = (REG_DIR / "main.tf").read_text(encoding="utf-8")
    outs_tf = (REG_DIR / "outputs.tf").read_text(encoding="utf-8")
    vars_tf = (REG_DIR / "variables.tf").read_text(encoding="utf-8")

    assert 'resource "aws_ecr_repository" "this"' in main_tf
    assert "image_tag_mutability = var.image_tag_mutability" in main_tf
    assert "scan_on_push = var.scan_on_push" in main_tf
    assert 'encryption_type = "AES256"' in main_tf
    assert 'resource "aws_ecr_lifecycle_policy" "this"' in main_tf
    assert 'variable "repository_name"' in vars_tf
    assert 'output "repository_url"' in outs_tf


def test_root_composition_wiring():
    """Verify root main.tf orchestrates networking, storage, and registries."""
    root_main = (TF_DIR / "main.tf").read_text(encoding="utf-8")
    assert 'module "networking"' in root_main
    assert 'module "document_storage"' in root_main
    assert 'module "api_registry"' in root_main
    assert 'module "worker_registry"' in root_main
    assert 'module "frontend_registry"' in root_main


def test_aws_networking_implementation_doc():
    """Verify AWS_NETWORKING_IMPLEMENTATION.md exists and covers architecture details."""
    doc_path = DOCS_DIR / "AWS_NETWORKING_IMPLEMENTATION.md"
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")
    assert "Target Network Topology & Traffic Flow" in content
    assert "Subnet Allocation & CIDR Matrix" in content
    assert "Route Table Design & Isolation Verification" in content
    assert "Security Group Chaining Matrix" in content
    assert "S3 Gateway VPC Endpoint Architecture" in content
    assert "Remaining Production Deployment Gaps" in content
