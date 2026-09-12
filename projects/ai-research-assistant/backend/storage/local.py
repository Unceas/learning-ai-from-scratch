"""Local filesystem implementation of the Storage interface."""

from pathlib import Path
import uuid
from backend.storage.base import Storage


class LocalStorage(Storage):

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
        safe_name = f"{uuid.uuid4()}_{filename}"
        file_path = self.base_path / safe_name
        with open(file_path, "wb") as file:
            file.write(content)
        return str(file_path)

    def delete(
        self,
        file_path: str
    ) -> None:
        path = Path(file_path)
        if path.exists():
            path.unlink()
