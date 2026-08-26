"""Authentication API routes for user registration and JWT login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas.requests import RegisterRequest, LoginRequest
from backend.schemas.responses import TokenResponse
from backend.services.user_service import create_user, authenticate_user
from backend.services.auth_service import create_access_token

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user in persistent database and return JWT bearer token."""
    created = create_user(
        db,
        request.user_id,
        request.password
    )
    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists."
        )

    token = create_access_token(request.user_id)
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user credentials against persistent database and return JWT bearer token."""
    authenticated = authenticate_user(
        db,
        request.user_id,
        request.password
    )
    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials."
        )

    token = create_access_token(request.user_id)
    return {
        "access_token": token,
        "token_type": "bearer"
    }
