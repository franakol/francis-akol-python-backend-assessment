"""User management endpoints."""

from typing import Optional

from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    MessageResponse,
    PaginatedUserResponse,
    ProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.user_service import UserService
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current authenticated user's profile.

    Requires authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    return await user_service.get_current_user_profile(current_user.id)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's information.

    - **email**: New email (optional, must be unique)
    - **username**: New username (optional, must be unique)

    Requires authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    return await user_service.update_current_user(current_user.id, update_data)


@router.put("/me/profile", response_model=UserResponse)
async def update_current_user_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user's profile.

    - **first_name**: First name (optional)
    - **last_name**: Last name (optional)
    - **bio**: Bio/description (optional)
    - **avatar_url**: Avatar image URL (optional)

    Requires authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    return await user_service.update_current_user_profile(
        current_user.id, profile_data
    )


@router.get("/", response_model=PaginatedUserResponse)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of users (admin only).

    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 10, max: 100)
    - **role**: Filter by role (optional)

    Requires admin authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    return await user_service.get_users(
        page=page, page_size=page_size, role=role
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user by ID (admin only).

    - **user_id**: User ID

    Requires admin authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    return await user_service.get_user_by_id(user_id)


@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user by ID (admin only).

    - **user_id**: User ID to delete

    Note: Cannot delete your own account.
    Requires admin authentication.
    """
    user_repository = UserRepository(db)
    user_service = UserService(user_repository)
    await user_service.delete_user(user_id, current_user.id)
    return MessageResponse(message=f"User {user_id} deleted successfully")
