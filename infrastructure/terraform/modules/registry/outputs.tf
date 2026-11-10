output "repository_urls" {
  description = "List of all ECR repository URLs created by this module"
  value       = aws_ecr_repository.this[*].repository_url
}

output "repository_arns" {
  description = "List of all ECR repository ARNs created by this module"
  value       = aws_ecr_repository.this[*].arn
}

output "repository_url" {
  description = "The primary or single ECR repository URL"
  value       = try(aws_ecr_repository.this[0].repository_url, "")
}

output "repository_arn" {
  description = "The primary or single ECR repository ARN"
  value       = try(aws_ecr_repository.this[0].arn, "")
}
