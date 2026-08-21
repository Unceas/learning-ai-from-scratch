"""Persistent JSON document registry for tracking user-scoped document hashes and indexing metadata."""

import json
import os

REGISTRY_PATH = "./document_registry.json"


def load_registry() -> dict:
    """Load persistent registry dictionary from JSON file."""
    if not os.path.exists(REGISTRY_PATH):
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_registry(registry: dict) -> None:
    """Save persistent registry dictionary to JSON file."""
    with open(REGISTRY_PATH, "w", encoding="utf-8") as file:
        json.dump(registry, file, indent=4)


def get_document(user_id: str, file_hash: str) -> dict:
    """Retrieve document indexing record by user_id and SHA-256 file_hash."""
    registry = load_registry()
    user_documents = registry.get(user_id, {})
    return user_documents.get(file_hash)


def register_document(user_id: str, file_hash: str, filename: str, chunks: int) -> None:
    """Register indexed document under user_id and file_hash."""
    registry = load_registry()
    if user_id not in registry:
        registry[user_id] = {}

    registry[user_id][file_hash] = {
        "filename": filename,
        "chunks": chunks
    }

    save_registry(registry)
