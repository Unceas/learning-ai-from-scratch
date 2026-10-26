"""Storage package initializing global storage instance."""

from backend.storage.factory import get_storage

storage = get_storage()

__all__ = ["get_storage", "storage"]
