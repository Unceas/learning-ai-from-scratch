"""In-memory user store service for authentication and user validation."""

from backend.services.auth_service import (
    hash_password,
    verify_password
)

users = {}


def create_user(
    user_id: str,
    password: str
) -> bool:
    """Register a new user with hashed password. Returns False if user already exists."""
    if user_id in users:
        return False

    users[user_id] = {
        "password_hash": hash_password(password)
    }
    return True


def authenticate_user(
    user_id: str,
    password: str
) -> bool:
    """Validate credentials against user store. Returns True if valid."""
    user = users.get(user_id)
    if not user:
        return False

    return verify_password(
        password,
        user["password_hash"]
    )
