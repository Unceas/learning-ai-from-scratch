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

    @abstractmethod
    def read(
        self,
        file_path: str
    ) -> bytes:
        """Read and return binary file content by storage path / key identifier."""

    @abstractmethod
    def exists(
        self,
        file_path: str
    ) -> bool:
        """Check whether file exists at storage path / key identifier."""

    @abstractmethod
    def delete(
        self,
        file_path: str
    ) -> None:
        """Delete file by storage path / reference identifier."""
