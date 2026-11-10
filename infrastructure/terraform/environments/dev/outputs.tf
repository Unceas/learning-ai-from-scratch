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

output "application_security_group_id" {
  description = "Dev Application Security Group ID"
  value       = module.dev_infrastructure.application_security_group_id
}

output "database_security_group_id" {
  description = "Dev Database Security Group ID"
  value       = module.dev_infrastructure.database_security_group_id
}

output "nat_gateway_id" {
  description = "Dev NAT Gateway ID"
  value       = module.dev_infrastructure.nat_gateway_id
}

output "s3_endpoint_id" {
  description = "Dev S3 Endpoint ID"
  value       = module.dev_infrastructure.s3_endpoint_id
}
