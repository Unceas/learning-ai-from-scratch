"""SHA-256 document hashing module for content-based fingerprinting."""

import hashlib


def calculate_file_hash(file) -> str:
    """Calculate deterministic SHA-256 hex digest for a file object while preserving file seek position."""
    file.seek(0)
    content = file.read()
    file.seek(0)
    return hashlib.sha256(content).hexdigest()
