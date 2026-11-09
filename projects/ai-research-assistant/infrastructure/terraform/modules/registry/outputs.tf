output "repository_urls" {
  description = "Map of ECR repository URLs"
  value = {
    for idx, repo in aws_ecr_repository.this : repo.name => repo.repository_url
  }
}

output "repository_arns" {
  description = "Map of ECR repository ARNs"
  value = {
    for idx, repo in aws_ecr_repository.this : repo.name => repo.arn
  }
}
