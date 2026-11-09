output "vpc_id" {
  description = "Dev VPC ID"
  value       = module.dev_infrastructure.vpc_id
}

output "documents_bucket_name" {
  description = "Dev S3 Bucket Name"
  value       = module.dev_infrastructure.documents_bucket_name
}

output "container_repository_urls" {
  description = "Dev ECR Repository URLs"
  value       = module.dev_infrastructure.container_repository_urls
}
