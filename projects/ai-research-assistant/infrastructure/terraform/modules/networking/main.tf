# ==============================================================================
# AWS Networking Module: 3-Tier Multi-AZ VPC with NAT & S3 Gateway Endpoint
# ==============================================================================

# Virtual Private Cloud (VPC)
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(var.tags, {
    Name = "${var.name}-vpc"
  })
}

# Internet Gateway for Public Egress/Ingress
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-igw"
  })
}

# ------------------------------------------------------------------------------
# Subnets across Availability Zones
# ------------------------------------------------------------------------------

# Public Subnets (ALB & NAT Gateways)
resource "aws_subnet" "public" {
  count = length(var.public_subnets)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name}-public-${count.index + 1}"
    Tier = "public"
  })
}

# Private Application Subnets (API & Workers)
resource "aws_subnet" "private" {
  count = length(var.private_subnets)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.private_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${var.name}-private-${count.index + 1}"
    Tier = "application"
  })
}

# Isolated Database Subnets (PostgreSQL, Redis, Vector DB)
resource "aws_subnet" "database" {
  count = length(var.database_subnets)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = var.database_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${var.name}-database-${count.index + 1}"
    Tier = "data"
  })
}

# ------------------------------------------------------------------------------
# Public Routing & Internet Gateway Association
# ------------------------------------------------------------------------------

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.this.id
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# ------------------------------------------------------------------------------
# NAT Gateway for Outbound Private Egress
# ------------------------------------------------------------------------------

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name}-nat-eip"
  })
}

resource "aws_nat_gateway" "this" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id

  depends_on = [
    aws_internet_gateway.this
  ]

  tags = merge(var.tags, {
    Name = "${var.name}-nat"
  })
}

# ------------------------------------------------------------------------------
# Private Routing & NAT Gateway Associations
# ------------------------------------------------------------------------------

resource "aws_route_table" "private" {
  count = length(aws_subnet.private)

  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route" "private_nat" {
  count = length(aws_route_table.private)

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this.id
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ------------------------------------------------------------------------------
# Isolated Database Routing (Strictly NO Default Route to Internet or NAT)
# ------------------------------------------------------------------------------

resource "aws_route_table" "database" {
  count = length(aws_subnet.database)

  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-database-rt-${count.index + 1}"
  })
}

resource "aws_route_table_association" "database" {
  count = length(aws_subnet.database)

  subnet_id      = aws_subnet.database[count.index].id
  route_table_id = aws_route_table.database[count.index].id
}

# ------------------------------------------------------------------------------
# Security Groups: Principle of Least Privilege
# ------------------------------------------------------------------------------

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name        = "${var.name}-alb-sg"
  description = "Internet-facing Application Load Balancer security group"
  vpc_id      = aws_vpc.this.id

  ingress {
    description = "HTTPS ingress from public internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP ingress from public internet for redirect"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic to application targets"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name}-alb-sg"
  })
}

# Application Workloads Security Group (FastAPI API & Ingestion Workers)
resource "aws_security_group" "application" {
  name        = "${var.name}-application-sg"
  description = "Application workload security group"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "HTTP traffic from Application Load Balancer"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound traffic for external LLM API and dependencies"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name}-application-sg"
  })
}

# Database Security Group (PostgreSQL Metadata Store)
resource "aws_security_group" "database" {
  name        = "${var.name}-database-sg"
  description = "PostgreSQL access from application workloads"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "PostgreSQL from application workloads"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    description = "Database outbound response traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name}-database-sg"
  })
}

# Redis Cache & Task Queue Security Group
resource "aws_security_group" "redis" {
  name        = "${var.name}-redis-sg"
  description = "ElastiCache Redis access from application workloads"
  vpc_id      = aws_vpc.this.id

  ingress {
    description     = "Redis port 6379 from application workloads"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.application.id]
  }

  egress {
    description = "Redis outbound response traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name}-redis-sg"
  })
}

# ------------------------------------------------------------------------------
# S3 Gateway VPC Endpoint (Cost-Free Direct S3 Traffic Without NAT Egress)
# ------------------------------------------------------------------------------

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.this.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = concat(
    aws_route_table.private[*].id,
    aws_route_table.database[*].id
  )

  tags = merge(var.tags, {
    Name = "${var.name}-s3-endpoint"
  })
}
