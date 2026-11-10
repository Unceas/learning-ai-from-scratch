# ==============================================================================
# Root Infrastructure Composition for AI Research Assistant
# ==============================================================================

# Reusable S3 Document Storage Module
module "document_storage" {
  source = "./modules/storage"

  bucket_name       = var.documents_bucket_name
  enable_versioning = var.enable_versioning
  tags              = local.common_tags
}

# 3-Tier Multi-AZ VPC Networking Module
module "networking" {
  source = "./modules/networking"

  name               = local.name_prefix
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  public_subnets     = var.public_subnets
  private_subnets    = var.private_subnets
  database_subnets   = var.database_subnets
  tags               = local.common_tags
}

# Dedicated Container Registries (ECR) for Microservices
module "api_registry" {
  source = "./modules/registry"

  repository_name = "${local.name_prefix}-api"
  tags            = local.common_tags
}

module "worker_registry" {
  source = "./modules/registry"

  repository_name = "${local.name_prefix}-worker"
  tags            = local.common_tags
}

module "frontend_registry" {
  source = "./modules/registry"

  repository_name = "${local.name_prefix}-frontend"
  tags            = local.common_tags
}

# Unified Container Registry Module
module "container_registry" {
  source = "./modules/registry"

  repository_names = [
    "${local.name_prefix}-backend",
    "${local.name_prefix}-frontend"
  ]
  tags = local.common_tags
}
