# ==============================================================================
# AWS ECR Registry Module: Container Repositories & Automated Lifecycle Policies
# ==============================================================================

locals {
  repositories = var.repository_name != "" ? [var.repository_name] : var.repository_names
}

resource "aws_ecr_repository" "this" {
  count = length(local.repositories)

  name                 = local.repositories[count.index]
  image_tag_mutability = var.image_tag_mutability

  image_scanning_configuration {
    scan_on_push = var.scan_on_push
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(var.tags, {
    ManagedBy = "Terraform"
  })
}

resource "aws_ecr_lifecycle_policy" "this" {
  count = length(local.repositories)

  repository = aws_ecr_repository.this[count.index].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Retain last 15 production images for safe deployment rollback"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-", "prod-"]
          countType     = "imageCountMoreThan"
          countNumber   = 15
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
