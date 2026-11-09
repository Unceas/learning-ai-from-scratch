variable "name" {
  description = "Base prefix for network resource naming"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of Availability Zones"
  type        = list(string)
}

variable "public_subnets" {
  description = "List of public subnet CIDRs"
  type        = list(string)
}

variable "private_subnets" {
  description = "List of private application subnet CIDRs"
  type        = list(string)
}

variable "database_subnets" {
  description = "List of isolated database subnet CIDRs"
  type        = list(string)
}

variable "tags" {
  description = "Additional tags for network resources"
  type        = map(string)
  default     = {}
}
