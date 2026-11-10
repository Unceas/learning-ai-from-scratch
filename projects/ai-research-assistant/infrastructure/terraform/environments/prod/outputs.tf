output "vpc_id" {
  description = "Prod VPC ID"
  value       = module.prod_infrastructure.vpc_id
}

output "documents_bucket_name" {
  description = "Prod S3 Bucket Name"
  value       = module.prod_infrastructure.documents_bucket_name
}

output "container_repository_urls" {
  description = "Prod ECR Repository URLs"
  value       = module.prod_infrastructure.container_repository_urls
}

output "application_security_group_id" {
  description = "Prod Application Security Group ID"
  value       = module.prod_infrastructure.application_security_group_id
}

output "database_security_group_id" {
  description = "Prod Database Security Group ID"
  value       = module.prod_infrastructure.database_security_group_id
}

output "nat_gateway_id" {
  description = "Prod NAT Gateway ID"
  value       = module.prod_infrastructure.nat_gateway_id
}

output "s3_endpoint_id" {
  description = "Prod S3 Endpoint ID"
  value       = module.prod_infrastructure.s3_endpoint_id
}
