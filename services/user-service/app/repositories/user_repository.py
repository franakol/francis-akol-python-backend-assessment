"""User repository for database operations."""

from typing import Optional

from app.models.user import Profile, User, UserRole
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class UserRepository:
    """Repository for User database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        role: UserRole = UserRole.STUDENT,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID with profile."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email with profile."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with profile."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email_or_username(
        self, email: str, username: str
    ) -> Optional[User]:
        """Get user by email or username."""
        result = await self.db.execute(
            select(User).where(
                or_(User.email == email, User.username == username)
            )
        )
        return result.scalar_one_or_none()

    async def get_users(
        self, skip: int = 0, limit: int = 100, role: Optional[UserRole] = None
    ) -> list[User]:
        """Get list of users with pagination and optional role filter."""
        query = (
            select(User)
            .options(selectinload(User.profile))
            .offset(skip)
            .limit(limit)
        )

        if role:
            query = query.where(User.role == role)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_users(self, role: Optional[UserRole] = None) -> int:
        """Count total users with optional role filter."""
        query = select(func.count()).select_from(User)

        if role:
            query = query.where(User.role == role)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_user(self, user: User) -> User:
        """Update user."""
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user: User) -> None:
        """Delete user."""
        await self.db.delete(user)
        await self.db.commit()

    async def create_profile(self, user_id: int, **profile_data) -> Profile:
        """Create user profile."""
        profile = Profile(user_id=user_id, **profile_data)
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def get_profile_by_user_id(self, user_id: int) -> Optional[Profile]:
        """Get profile by user ID."""
        result = await self.db.execute(
            select(Profile).where(Profile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_profile(self, profile: Profile) -> Profile:
        """Update profile."""
        await self.db.commit()
        await self.db.refresh(profile)
        return profile
