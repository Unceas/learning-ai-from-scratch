"""Storage package initializing global storage instance."""

from backend.storage.base import Storage
from backend.storage.factory import get_storage
from backend.storage.local import has_pdf_signature, safe_storage_path
from backend.storage.s3 import S3Storage

storage = get_storage()

__all__ = ["Storage", "S3Storage", "get_storage", "has_pdf_signature", "safe_storage_path", "storage"]
