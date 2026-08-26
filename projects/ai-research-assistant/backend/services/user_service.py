"""Database-backed user store service for persistent authentication."""

from sqlalchemy.orm import Session
from backend.models import User
from backend.services.auth_service import (
    hash_password,
    verify_password
)


def create_user(
    db: Session,
    user_id: str,
    password: str
) -> bool:
    """Register a new user with hashed password in persistent SQLite database. Returns False if user exists."""
    existing = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if existing:
        return False

    user = User(
        id=user_id,
        password_hash=hash_password(password)
    )

    db.add(user)
    db.commit()
    return True


def authenticate_user(
    db: Session,
    user_id: str,
    password: str
) -> bool:
    """Authenticate credentials against persistent SQLite database."""
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        return False

    return verify_password(
        password,
        user.password_hash
    )
