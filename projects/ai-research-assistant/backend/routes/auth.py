"""Authentication API routes for user registration and JWT login."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.schemas.requests import LoginRequest, RegisterRequest
from backend.schemas.responses import TokenResponse, UserResponse
from backend.services.auth_service import create_access_token
from backend.services.rate_limiter import rate_limiter
from backend.services.user_service import authenticate_user, create_user

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
def register(
    http_request: Request,
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """Register a new user in persistent database and return JWT bearer token."""
    rate_limiter.enforce(
        http_request,
        scope="auth",
        limit=getattr(settings, "auth_rate_limit_per_minute", 30),
    )
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
    http_request: Request,
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user credentials against persistent database and return JWT bearer token."""
    rate_limiter.enforce(
        http_request,
        scope="auth",
        limit=getattr(settings, "auth_rate_limit_per_minute", 30),
    )
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


@router.get("/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user)):
    """Return the currently authenticated user identity."""
    return {
        "id": user_id,
        "username": user_id,
        "user_id": user_id
    }

