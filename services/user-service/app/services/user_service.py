"""User service for user management operations."""

import math
from typing import Optional

from app.models.user import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    PaginatedUserResponse,
    ProfileUpdateRequest,
    UserResponse,
    UserUpdateRequest,
)
from fastapi import HTTPException, status


class UserService:
    """Service for user management operations."""

    def __init__(self, user_repository: UserRepository):
        """Initialize user service with user repository."""
        self.user_repository = user_repository

    async def get_user_by_id(self, user_id: int) -> UserResponse:
        """Get user by ID."""
        user = await self.user_repository.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse.model_validate(user)

    async def get_current_user_profile(self, user_id: int) -> UserResponse:
        """Get current user's profile."""
        return await self.get_user_by_id(user_id)

    async def update_current_user(
        self, user_id: int, update_data: UserUpdateRequest
    ) -> UserResponse:
        """Update current user's information."""
        user = await self.user_repository.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Check if email is being updated and if it's already taken
        if update_data.email and update_data.email != user.email:
            existing_user = await self.user_repository.get_user_by_email(
                update_data.email
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            user.email = update_data.email

        # Check if username is being updated and if it's already taken
        if update_data.username and update_data.username != user.username:
            existing_user = await self.user_repository.get_user_by_username(
                update_data.username
            )
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken",
                )
            user.username = update_data.username

        user = await self.user_repository.update_user(user)
        return UserResponse.model_validate(user)

    async def update_current_user_profile(
        self, user_id: int, profile_data: ProfileUpdateRequest
    ) -> UserResponse:
        """Update current user's profile."""
        user = await self.user_repository.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Get or create profile
        profile = await self.user_repository.get_profile_by_user_id(user_id)

        if not profile:
            # Create profile if it doesn't exist
            profile = await self.user_repository.create_profile(
                user_id=user_id,
                **profile_data.model_dump(exclude_unset=True),
            )
        else:
            # Update existing profile
            update_dict = profile_data.model_dump(exclude_unset=True)
            for key, value in update_dict.items():
                setattr(profile, key, value)

            profile = await self.user_repository.update_profile(profile)

        # Refresh user to get updated profile
        user = await self.user_repository.get_user_by_id(user_id)
        return UserResponse.model_validate(user)

    async def get_users(
        self,
        page: int = 1,
        page_size: int = 10,
        role: Optional[UserRole] = None,
    ) -> PaginatedUserResponse:
        """Get paginated list of users."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        skip = (page - 1) * page_size

        # Get users and total count
        users = await self.user_repository.get_users(
            skip=skip, limit=page_size, role=role
        )
        total = await self.user_repository.count_users(role=role)

        # Calculate total pages
        total_pages = math.ceil(total / page_size)

        return PaginatedUserResponse(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def delete_user(self, user_id: int, current_user_id: int) -> None:
        """Delete a user (admin only, cannot delete self)."""
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account",
            )

        user = await self.user_repository.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        await self.user_repository.delete_user(user)
