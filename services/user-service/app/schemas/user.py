"""Pydantic schemas for User Service."""

from datetime import datetime
from typing import Optional

from app.models.user import UserRole
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Base schemas
class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str = Field(
        ..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$"
    )


class ProfileBase(BaseModel):
    """Base profile schema with common fields."""

    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=500)


# Request schemas
class UserSignupRequest(UserBase):
    """Schema for user registration request."""

    password: str = Field(..., min_length=8, max_length=100)
    role: Optional[UserRole] = UserRole.STUDENT


class UserLoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class UserUpdateRequest(BaseModel):
    """Schema for user update request."""

    email: Optional[EmailStr] = None
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$"
    )


class ProfileUpdateRequest(ProfileBase):
    """Schema for profile update request."""

    pass


class TokenRefreshRequest(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str


# Response schemas
class ProfileResponse(ProfileBase):
    """Schema for profile response."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Schema for user response."""

    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[ProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class LoginResponse(BaseModel):
    """Schema for login response."""

    user: UserResponse
    tokens: TokenResponse


class MessageResponse(BaseModel):
    """Schema for generic message response."""

    message: str


class PaginatedUserResponse(BaseModel):
    """Schema for paginated user list response."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
