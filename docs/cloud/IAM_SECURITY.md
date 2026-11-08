# IAM Strategy & Cloud Security Architecture

## 1. Zero-Credential Philosophy & Workload Identity

A foundational rule of our cloud infrastructure:

> **Core IAM Invariant**: Static, long-lived AWS Access Keys (`AKIA...`) must NEVER be committed to source repositories, baked into container images, or stored in environment variable files. Every workload and CI/CD runner must assume scoped, short-lived IAM credentials via temporary STS tokens.

### Workload Identity Mechanisms

| Compute Platform | Identity Mechanism | Credential Delivery |
|---|---|---|
| **Amazon ECS** | **ECS Task Role** | Injected via AWS Container Credentials URI (`AWS_CONTAINER_CREDENTIALS_RELATIVE_URI`), rotated automatically by AWS every 6 hours. |
| **Amazon EKS** | **EKS Pod Identity / IRSA** | OIDC token projected into Pod volume, exchanged with AWS STS for temporary IAM role credentials. |
| **GitHub Actions** | **OIDC Federation** | GitHub Actions requests an OpenID Connect token from GitHub, validated by AWS IAM without storing `AWS_ACCESS_KEY_ID`. |

---

## 2. Granular Task & Worker Role Definitions

Amazon ECS separates container initialization permissions from application runtime permissions:
- **Task Execution Role**: Used by the ECS agent to pull images from ECR and fetch initial secrets from Secrets Manager.
- **Task Role**: Used by the application code inside the running container to access AWS services (S3, SQS, KMS).

### 1. API Service Task Role (`role-ai-research-api`)
The API service requires permissions to generate S3 presigned URLs, enqueue indexing tasks, and decrypt application secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DocumentAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::prod-ai-research-assistant-documents",
        "arn:aws:s3:::prod-ai-research-assistant-documents/*"
      ]
    },
    {
      "Sid": "SQSTaskEnqueue",
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:document-indexing"
    },
    {
      "Sid": "SecretsManagerRead",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/research-assistant/*"
    },
    {
      "Sid": "KMSDecrypt",
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:123456789012:key/mrk-research-key"
    }
  ]
}
```

### 2. Ingestion Worker Task Role (`role-ai-research-worker`)
The worker process requires permissions to consume messages from SQS, read/write document artifacts in S3, and report dead letters:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SQSConsumeAndAcknowledge",
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:ChangeMessageVisibility",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:document-indexing"
    },
    {
      "Sid": "SQSSendToDeadLetterQueue",
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:indexing-dlq"
    },
    {
      "Sid": "S3ObjectReadAndChunkStorage",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::prod-ai-research-assistant-documents/*"
    },
    {
      "Sid": "SecretsAndKMSAccess",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/research-assistant/*",
        "arn:aws:kms:us-east-1:123456789012:key/mrk-research-key"
      ]
    }
  ]
}
```

---

## 3. GitHub Actions CI/CD Deployment Role (OIDC Federation)

GitHub Actions assumes an IAM role using OIDC trust policy without static credentials:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:Unceas/learning-ai-from-scratch:ref:refs/tags/v*"
        }
      }
    }
  ]
}
```

### Deployment Policy Permissions:
- `ecr:GetAuthorizationToken`, `ecr:BatchCheckLayerAvailability`, `ecr:PutImage`, `ecr:InitiateLayerUpload`.
- `ecs:UpdateService`, `ecs:RegisterTaskDefinition`, `ecs:DescribeServices`.
- `s3:Sync` (scoped exclusively to the frontend bucket).
- `cloudfront:CreateInvalidation` (to clear cached SPA distribution upon release).

---

## 4. Secrets Management Strategy

1. **AWS Secrets Manager**:
   - Stores high-value credentials that require automatic rotation: PostgreSQL master password, JWT signing private keys, and external LLM provider API keys.
   - Rotates RDS credentials automatically every 30 days via managed Lambda.
2. **SSM Parameter Store (Standard Tier)**:
   - Stores non-sensitive, environment-specific configuration strings (e.g. `/prod/config/APP_ENV`, `/prod/config/EMBEDDING_MODEL`) free of API call charges.
3. **No Secrets in Frontend**:
   - The React frontend receives **only** public endpoints (`VITE_API_BASE_URL`). All LLM calls and database queries are brokered exclusively through the authenticated FastAPI backend.

---

## 5. Encryption at Rest & In Transit

| Resource | Encryption at Rest | Encryption in Transit | Key Management |
|---|---|---|---|
| **S3 Buckets** | Server-Side Encryption with AWS KMS (`SSE-KMS`) | HTTPS / TLS 1.3 only (enforced via bucket policy `aws:SecureTransport`) | Customer-Managed KMS Key (CMK) |
| **Amazon RDS** | AES-256 storage volume encryption | TLS required (`sslmode=require` in SQLAlchemy connection string) | Customer-Managed KMS Key (CMK) |
| **ElastiCache Redis** | Encrypted in-memory storage & snapshots | In-transit TLS with Redis AUTH token | AWS Managed KMS Key |
| **ALB / CloudFront** | N/A (Stateless) | TLS 1.3 enforced with modern cipher suites | AWS Certificate Manager (ACM) |
| **CloudWatch Logs** | Encrypted log groups | HTTPS API streaming | Customer-Managed KMS Key (CMK) |
