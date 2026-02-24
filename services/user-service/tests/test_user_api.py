"""Tests for user management API endpoints."""

import pytest
from httpx import AsyncClient


async def create_test_user(
    client: AsyncClient,
    email: str = "test@example.com",
    username: str = "testuser",
    role: str = "student",
):
    """Helper function to create a test user and return tokens."""
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "username": username,
            "password": "SecurePass123!",
            "role": role,
        },
    )
    data = response.json()
    return data["user"], data["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    """Test getting current user's profile."""
    user, access_token = await create_test_user(client)

    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user["email"]
    assert data["username"] == user["username"]


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without authentication fails."""
    response = await client.get("/api/v1/users/me")

    assert (
        response.status_code == 403
    )  # HTTPBearer returns 403 for missing token


@pytest.mark.asyncio
async def test_update_current_user(client: AsyncClient):
    """Test updating current user's information."""
    user, access_token = await create_test_user(client)

    response = await client.put(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "username": "newusername",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newusername"
    assert data["email"] == user["email"]  # Email unchanged


@pytest.mark.asyncio
async def test_update_current_user_profile(client: AsyncClient):
    """Test updating current user's profile."""
    user, access_token = await create_test_user(client)

    response = await client.put(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json={
            "first_name": "John",
            "last_name": "Doe",
            "bio": "Test bio",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["profile"]["first_name"] == "John"
    assert data["profile"]["last_name"] == "Doe"
    assert data["profile"]["bio"] == "Test bio"


@pytest.mark.asyncio
async def test_get_users_list_admin_only(client: AsyncClient):
    """Test getting users list requires admin role."""
    # Create regular user
    user, access_token = await create_test_user(client, role="student")

    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403  # Forbidden


@pytest.mark.asyncio
async def test_get_users_list_admin(client: AsyncClient):
    """Test getting users list with admin role."""
    # Create admin user
    admin_user, admin_token = await create_test_user(
        client, email="admin@example.com", username="admin", role="admin"
    )

    # Create some regular users
    await create_test_user(client, email="user1@example.com", username="user1")
    await create_test_user(client, email="user2@example.com", username="user2")

    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 3  # At least admin + 2 users


@pytest.mark.asyncio
async def test_delete_user_admin_only(client: AsyncClient):
    """Test deleting user requires admin role."""
    # Create regular user
    user, access_token = await create_test_user(client)

    # Create another user to try to delete
    user2, _ = await create_test_user(
        client, email="user2@example.com", username="user2"
    )

    response = await client.delete(
        f"/api/v1/users/{user2['id']}",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403  # Forbidden
