terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "ai-research-assistant-tfstate-bootstrap"
    key          = "ai-research-assistant/dev/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AIResearchAssistant"
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}

module "dev_infrastructure" {
  source = "../../"

  aws_region            = var.aws_region
  environment           = "dev"
  documents_bucket_name = var.documents_bucket_name
  enable_versioning     = var.enable_versioning
  vpc_cidr              = var.vpc_cidr
  availability_zones    = var.availability_zones
  public_subnets        = var.public_subnets
  private_subnets       = var.private_subnets
  database_subnets      = var.database_subnets
}
