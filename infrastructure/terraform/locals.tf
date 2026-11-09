locals {
  name_prefix = "research-assistant-${var.environment}"

  common_tags = {
    Project     = "AIResearchAssistant"
    Application = "AIResearchAssistant"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
