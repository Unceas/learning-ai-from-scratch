provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AIResearchAssistant"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
