output "vpc_id" {
  description = "Production VPC ID"
  value       = module.prod_infrastructure.vpc_id
}

output "documents_bucket_name" {
  description = "Production S3 Bucket Name"
  value       = module.prod_infrastructure.documents_bucket_name
}

output "container_repository_urls" {
  description = "Production ECR Repository URLs"
  value       = module.prod_infrastructure.container_repository_urls
}
