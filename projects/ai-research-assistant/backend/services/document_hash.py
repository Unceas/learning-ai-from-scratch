"""SHA-256 document hashing module for content-based fingerprinting."""

import hashlib
from typing import Union


def calculate_file_hash(file_or_content: Union[bytes, bytearray, object]) -> str:
    """Calculate deterministic SHA-256 hex digest for a file object or raw bytes."""
    if isinstance(file_or_content, (bytes, bytearray)):
        content = file_or_content
    elif hasattr(file_or_content, "read"):
        if hasattr(file_or_content, "seek"):
            file_or_content.seek(0)
        content = file_or_content.read()
        if hasattr(file_or_content, "seek"):
            file_or_content.seek(0)
    else:
        content = bytes(file_or_content)
    return hashlib.sha256(content).hexdigest()
