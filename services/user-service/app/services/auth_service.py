"""Authentication service for user authentication and authorization."""

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    LoginResponse,
    TokenResponse,
    UserResponse,
    UserSignupRequest,
)
from fastapi import HTTPException, status


class AuthService:
    """Service for authentication operations."""

    def __init__(self, user_repository: UserRepository):
        """Initialize auth service with user repository."""
        self.user_repository = user_repository

    async def signup(self, signup_data: UserSignupRequest) -> LoginResponse:
        """Register a new user."""
        # Check if user already exists
        existing_user = (
            await self.user_repository.get_user_by_email_or_username(
                email=signup_data.email, username=signup_data.username
            )
        )

        if existing_user:
            if existing_user.email == signup_data.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )

        # Hash password
        hashed_password = hash_password(signup_data.password)

        # Create user
        user = await self.user_repository.create_user(
            email=signup_data.email,
            username=signup_data.username,
            hashed_password=hashed_password,
            role=signup_data.role or UserRole.STUDENT,
        )

        # Create empty profile
        await self.user_repository.create_profile(user_id=user.id)

        # Refresh user to get profile
        user = await self.user_repository.get_user_by_id(user.id)

        # Generate tokens
        tokens = self._generate_tokens(user)

        return LoginResponse(
            user=UserResponse.model_validate(user), tokens=tokens
        )

    async def login(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and return tokens."""
        # Get user by email
        user = await self.user_repository.get_user_by_email(email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Verify password
        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Generate tokens
        tokens = self._generate_tokens(user)

        return LoginResponse(
            user=UserResponse.model_validate(user), tokens=tokens
        )

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        from app.core.security import decode_token, verify_token_type

        try:
            # Decode and verify refresh token
            payload = decode_token(refresh_token)
            verify_token_type(payload, "refresh")

            user_id = int(payload.get("sub"))

            # Get user
            user = await self.user_repository.get_user_by_id(user_id)

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            # Generate new tokens
            tokens = self._generate_tokens(user)
            return tokens

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            ) from e

    def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access and refresh tokens for user."""
        # Token data
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role.value,
        }

        # Generate access token
        access_token = create_access_token(data=token_data)

        # Generate refresh token
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
