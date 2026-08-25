"""Authentication service providing password hashing, JWT generation, and token verification."""

from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt
from backend.config import settings


def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    pwd_bytes = password.encode("utf-8")[:72]
    return bcrypt.checkpw(pwd_bytes, password_hash.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    """Create signed JWT bearer token containing user_id and expiration."""
    expire = (
        datetime.now(timezone.utc)
        + timedelta(minutes=settings.jwt_expire_minutes)
    )

    payload = {
        "sub": user_id,
        "exp": expire
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate signed JWT token."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm]
    )
