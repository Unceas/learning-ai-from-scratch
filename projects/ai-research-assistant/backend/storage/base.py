"""Abstract base storage interface for document file persistence."""

from abc import ABC, abstractmethod


class Storage(ABC):

    @abstractmethod
    def save(
        self,
        filename: str,
        content: bytes
    ) -> str:
        """Save file content and return storage path / reference identifier."""
        pass

    @abstractmethod
    def delete(
        self,
        file_path: str
    ) -> None:
        """Delete file by storage path / reference identifier."""
        pass
