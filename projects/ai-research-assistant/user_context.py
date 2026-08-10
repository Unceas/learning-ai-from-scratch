"""User context module providing session user identity helpers."""

import uuid


def create_user_id() -> str:
    """Generate a unique random UUID v4 user identifier."""
    return str(uuid.uuid4())
