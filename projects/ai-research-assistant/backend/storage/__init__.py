"""Storage package initializing global storage instance."""

from backend.storage.factory import get_storage
from backend.storage.local import has_pdf_signature, safe_storage_path

storage = get_storage()

__all__ = ["get_storage", "has_pdf_signature", "safe_storage_path", "storage"]
