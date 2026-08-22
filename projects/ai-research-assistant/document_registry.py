"""Persistent JSON document registry for tracking user-scoped document hashes and indexing metadata."""

import json
import os

REGISTRY_PATH = "./document_registry.json"


def load_registry():
    """Load persistent registry dictionary from JSON file."""
    if not os.path.exists(REGISTRY_PATH):
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_registry(registry):
    """Save persistent registry dictionary to JSON file."""
    with open(REGISTRY_PATH, "w", encoding="utf-8") as file:
        json.dump(registry, file, indent=4)


def get_document(user_id, file_hash):
    """Retrieve document indexing record by user_id and SHA-256 file_hash."""
    registry = load_registry()
    return registry.get(user_id, {}).get(file_hash)


def register_document(user_id, file_hash, filename, chunks):
    """Register indexed document under user_id and file_hash."""
    registry = load_registry()
    if user_id not in registry:
        registry[user_id] = {}

    registry[user_id][file_hash] = {
        "filename": filename,
        "chunks": chunks
    }

    save_registry(registry)


def list_documents(user_id):
    """List all registered documents for given user_id."""
    registry = load_registry()
    documents = registry.get(user_id, {})
    return [
        {
            "file_hash": file_hash,
            **data
        }
        for file_hash, data in documents.items()
    ]


def remove_document(user_id, file_hash):
    """Remove registered document entry from registry for given user_id and file_hash."""
    registry = load_registry()
    user_documents = registry.get(user_id, {})

    if file_hash not in user_documents:
        return False

    del user_documents[file_hash]
    registry[user_id] = user_documents
    save_registry(registry)
    return True
