"""FastAPI dependency providers for authentication and security scoping."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from backend.services.auth_service import decode_access_token
from backend.services.authorization import (
    get_owned_conversation,
    get_owned_document,
    get_owned_feedback,
    get_owned_message,
)

security = HTTPBearer()

__all__ = [
    "get_current_user",
    "get_owned_conversation",
    "get_owned_document",
    "get_owned_feedback",
    "get_owned_message",
    "security",
]


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract and validate JWT bearer token, returning authenticated user_id."""
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token."
            )

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token."
        )
