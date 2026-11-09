output "vpc_id" {
  description = "VPC Identifier"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "Public Subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Private Application Subnet IDs"
  value       = module.networking.private_subnet_ids
}

output "database_subnet_ids" {
  description = "Isolated Database Subnet IDs"
  value       = module.networking.database_subnet_ids
}

output "documents_bucket_name" {
  description = "Name of the S3 document storage bucket"
  value       = module.document_storage.bucket_name
}

output "documents_bucket_arn" {
  description = "ARN of the S3 document storage bucket"
  value       = module.document_storage.bucket_arn
}

output "container_repository_urls" {
  description = "ECR Container Repository URLs"
  value       = module.container_registry.repository_urls
}
