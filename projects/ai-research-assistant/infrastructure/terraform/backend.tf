# ==============================================================================
# Terraform Remote State Configuration (S3 Backend with State Locking)
# NOTE: The S3 state bucket must be bootstrapped independently prior to init.
# For local validation without AWS connection, initialize with:
#   terraform init -backend=false
# ==============================================================================

terraform {
  backend "s3" {
    bucket       = "ai-research-assistant-tfstate-bootstrap"
    key          = "ai-research-assistant/terraform.tfstate"
    region       = "ap-south-1"
    encrypt      = true
    use_lockfile = true
  }
}
