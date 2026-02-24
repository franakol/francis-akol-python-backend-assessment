"""Authentication endpoints."""

from app.core.dependencies import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    LoginResponse,
    MessageResponse,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserSignupRequest,
)
from app.services.auth_service import AuthService
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/signup",
    response_model=LoginResponse,
    status_code=status.HTTP_201_CREATED,
)
async def signup(
    signup_data: UserSignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    - **email**: Valid email address (unique)
    - **username**: Username (3-50 chars, alphanumeric, unique)
    - **password**: Password (min 8 chars)
    - **role**: User role (STUDENT, INSTRUCTOR, ADMIN) - defaults to STUDENT

    Returns user info and authentication tokens.
    """
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)
    return await auth_service.signup(signup_data)


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: User password

    Returns user info and authentication tokens.
    """
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)
    return await auth_service.login(login_data.email, login_data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access and refresh tokens.
    """
    user_repository = UserRepository(db)
    auth_service = AuthService(user_repository)
    return await auth_service.refresh_token(refresh_data.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    Logout user (client-side token invalidation).

    Note: Tokens should be removed from client storage.
    Server-side token blacklisting can be implemented with Redis.
    """
    return MessageResponse(message="Successfully logged out")
