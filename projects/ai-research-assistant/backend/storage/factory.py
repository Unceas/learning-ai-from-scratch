"""Factory function to resolve configured Storage implementation."""

from backend.config import get_settings
from backend.storage.base import Storage
from backend.storage.local import LocalStorage


def get_storage() -> Storage:
    """Instantiate and return the configured storage backend."""
    settings = get_settings()

    if settings.storage_type == "local":
        return LocalStorage(settings.storage_path)

    raise ValueError(
        f"Unsupported storage type: {settings.storage_type}"
    )
