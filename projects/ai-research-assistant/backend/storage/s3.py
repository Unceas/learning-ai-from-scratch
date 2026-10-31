"""Shared S3-compatible object storage backend for multi-worker horizontal deployments."""

import uuid
from pathlib import Path
from typing import Any

from backend.storage.base import Storage


class S3Storage(Storage):
    """Shared object storage implementation supporting AWS S3, Cloudflare R2, and MinIO."""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        region_name: str = "us-east-1",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        client: Any = None,
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name
        self._client = client

        if self._client is None:
            try:
                import boto3
                session = boto3.session.Session()
                self._client = session.client(
                    "s3",
                    region_name=self.region_name,
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
            except ImportError:
                # Allow instantiation without boto3 if mock client is provided later
                self._client = None

    @property
    def client(self):
        if self._client is None:
            raise RuntimeError(
                "S3 client is not configured. Install boto3 or provide a storage client."
            )
        return self._client

    @staticmethod
    def _extract_key(file_path: str) -> str:
        """Extract object key from s3:// URI or relative key path."""
        if file_path.startswith("s3://"):
            parts = file_path[5:].split("/", 1)
            return parts[1] if len(parts) > 1 else parts[0]
        return file_path

    def save(
        self,
        filename: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        """Upload document bytes to shared bucket and return storage URI."""
        clean_name = Path(filename).name or "document.pdf"
        key = f"documents/{uuid.uuid4()}_{clean_name}"

        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        return f"s3://{self.bucket_name}/{key}"

    def read(
        self,
        file_path: str,
    ) -> bytes:
        """Retrieve binary document content from object storage."""
        key = self._extract_key(file_path)
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            body = response.get("Body")
            if hasattr(body, "read"):
                return body.read()
            return bytes(body or b"")
        except Exception as exc:
            raise FileNotFoundError(f"Object {key} not found in bucket {self.bucket_name}: {exc}") from exc

    def exists(
        self,
        file_path: str,
    ) -> bool:
        """Check whether object exists in bucket."""
        key = self._extract_key(file_path)
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=key,
            )
            return True
        except Exception:
            return False

    def delete(
        self,
        file_path: str,
    ) -> None:
        """Delete object from bucket."""
        key = self._extract_key(file_path)
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key,
            )
        except Exception:
            pass
