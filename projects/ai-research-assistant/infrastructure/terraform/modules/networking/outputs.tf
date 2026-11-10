output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.this.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private application subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "List of isolated database subnet IDs"
  value       = aws_subnet.database[*].id
}

output "public_route_table_id" {
  description = "The ID of the public route table"
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "List of private route table IDs"
  value       = aws_route_table.private[*].id
}

output "database_route_table_ids" {
  description = "List of database route table IDs"
  value       = aws_route_table.database[*].id
}

output "internet_gateway_id" {
  description = "The ID of the Internet Gateway"
  value       = aws_internet_gateway.this.id
}

output "nat_gateway_id" {
  description = "The ID of the NAT Gateway"
  value       = aws_nat_gateway.this.id
}

output "nat_eip" {
  description = "The Elastic IP address associated with the NAT Gateway"
  value       = aws_eip.nat.public_ip
}

output "s3_endpoint_id" {
  description = "The ID of the S3 Gateway VPC Endpoint"
  value       = aws_vpc_endpoint.s3.id
}

output "alb_security_group_id" {
  description = "The ID of the Application Load Balancer security group"
  value       = aws_security_group.alb.id
}

output "application_security_group_id" {
  description = "The ID of the application workload security group"
  value       = aws_security_group.application.id
}

output "database_security_group_id" {
  description = "The ID of the PostgreSQL database security group"
  value       = aws_security_group.database.id
}

output "redis_security_group_id" {
  description = "The ID of the Redis cache security group"
  value       = aws_security_group.redis.id
}
