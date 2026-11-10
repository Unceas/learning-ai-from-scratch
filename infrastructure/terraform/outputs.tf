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

output "public_route_table_id" {
  description = "Public route table identifier"
  value       = module.networking.public_route_table_id
}

output "private_route_table_ids" {
  description = "Private route table identifiers"
  value       = module.networking.private_route_table_ids
}

output "database_route_table_ids" {
  description = "Isolated database route table identifiers"
  value       = module.networking.database_route_table_ids
}

output "internet_gateway_id" {
  description = "Internet Gateway identifier"
  value       = module.networking.internet_gateway_id
}

output "nat_gateway_id" {
  description = "NAT Gateway identifier"
  value       = module.networking.nat_gateway_id
}

output "nat_eip" {
  description = "NAT Gateway Elastic IP"
  value       = module.networking.nat_eip
}

output "s3_endpoint_id" {
  description = "S3 Gateway VPC Endpoint identifier"
  value       = module.networking.s3_endpoint_id
}

output "alb_security_group_id" {
  description = "Application Load Balancer Security Group ID"
  value       = module.networking.alb_security_group_id
}

output "application_security_group_id" {
  description = "Application Workload Security Group ID"
  value       = module.networking.application_security_group_id
}

output "database_security_group_id" {
  description = "PostgreSQL Database Security Group ID"
  value       = module.networking.database_security_group_id
}

output "redis_security_group_id" {
  description = "Redis Cache Security Group ID"
  value       = module.networking.redis_security_group_id
}

output "documents_bucket_name" {
  description = "Name of the S3 document storage bucket"
  value       = module.document_storage.bucket_name
}

output "documents_bucket_arn" {
  description = "ARN of the S3 document storage bucket"
  value       = module.document_storage.bucket_arn
}

output "api_repository_url" {
  description = "ECR Repository URL for Backend API"
  value       = module.api_registry.repository_url
}

output "worker_repository_url" {
  description = "ECR Repository URL for Ingestion Workers"
  value       = module.worker_registry.repository_url
}

output "frontend_repository_url" {
  description = "ECR Repository URL for Frontend SPA"
  value       = module.frontend_registry.repository_url
}

output "container_repository_urls" {
  description = "ECR Container Repository URLs"
  value       = module.container_registry.repository_urls
}
