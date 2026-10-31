"""Factory function to resolve configured Storage implementation."""

from backend.config import get_settings
from backend.storage.base import Storage
from backend.storage.local import LocalStorage
from backend.storage.s3 import S3Storage


def get_storage() -> Storage:
    """Instantiate and return the configured storage backend."""
    settings = get_settings()

    if settings.storage_type == "local":
        return LocalStorage(settings.storage_path)

    if settings.storage_type == "s3":
        return S3Storage(
            bucket_name=settings.s3_bucket_name,
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key.get_secret_value() if settings.s3_access_key else None,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value() if settings.s3_secret_key else None,
        )

    raise ValueError(
        f"Unsupported storage type: {settings.storage_type}"
    )
