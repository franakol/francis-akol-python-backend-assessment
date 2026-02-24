"""FastAPI dependencies for dependency injection."""

from typing import Generator, Optional

from app.core.security import decode_token, verify_token_type
from app.db.session import async_session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

# Security scheme
security = HTTPBearer()


async def get_db() -> Generator[AsyncSession, None, None]:
    """
    Dependency to get database session.

    Yields:
        AsyncSession: Database session
    """
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dependency to get current authenticated user ID from JWT token.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        User ID from token

    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


async def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dependency to get current authenticated user email from JWT token.

    Args:
        credentials: HTTP Authorization credentials

    Returns:
        User email from token

    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")

    email: Optional[str] = payload.get("email")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return email


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency to get current authenticated user from database.

    Args:
        credentials: HTTP Authorization credentials
        db: Database session

    Returns:
        User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.models.user import User
    from sqlalchemy import select

    token = credentials.credentials
    payload = decode_token(token)
    verify_token_type(payload, "access")

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


def require_role(allowed_roles: list):
    """
    Dependency factory to check if user has required role.

    Args:
        allowed_roles: List of allowed UserRole enums

    Returns:
        Dependency function that returns User object
    """

    async def role_checker(
        current_user=Depends(get_current_user),
    ):
        # Convert UserRole enum to string for comparison
        allowed_role_values = [
            role.value if hasattr(role, "value") else role
            for role in allowed_roles
        ]

        if current_user.role.value not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_role_values)}",
            )

        return current_user

    return role_checker
