"""Local filesystem implementation of the Storage interface with path containment."""

import uuid
from pathlib import Path

from backend.storage.base import Storage


def safe_storage_path(
    storage_root: Path,
    filename: str,
) -> Path:
    """Validate that candidate path resides strictly within the storage root directory.

    Raises:
        ValueError: If candidate path escapes storage root (path traversal).
    """
    root = storage_root.resolve()
    candidate = (root / filename).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("Invalid storage path")
    return candidate


def has_pdf_signature(file_bytes: bytes) -> bool:
    """Check magic bytes for PDF document signature (%PDF-)."""
    return file_bytes.startswith(b"%PDF-")


class LocalStorage(Storage):
    """Local disk storage abstraction enforcing path containment and safe server-generated filenames."""

    def __init__(
        self,
        base_path: str = "uploads"
    ):
        self.base_path = Path(base_path)
        self.base_path.mkdir(
            parents=True,
            exist_ok=True
        )

    def save(
        self,
        filename: str,
        content: bytes
    ) -> str:
        # Strip client-supplied path traversal sequences
        clean_name = Path(filename).name or "document.pdf"
        safe_name = f"{uuid.uuid4()}_{clean_name}"

        # Defense-in-depth path containment verification
        file_path = safe_storage_path(self.base_path, safe_name)

        with open(file_path, "wb") as file:
            file.write(content)

        return str(file_path)

    def delete(
        self,
        file_path: str
    ) -> None:
        try:
            path = Path(file_path).resolve()
            root = self.base_path.resolve()
            if path.is_relative_to(root) and path.exists():
                path.unlink()
        except Exception:
            pass
