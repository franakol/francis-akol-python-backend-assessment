"""Tests for Enrollment API endpoints."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test the health check endpoint returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "enrollment-service"

    @pytest.mark.asyncio
    async def test_readiness_check(self, client: AsyncClient):
        """Test the readiness check endpoint."""
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint returns service info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Enrollment Service"
        assert "version" in data


class TestEnrollmentEndpoints:
    """Test enrollment API endpoints."""

    @pytest.mark.asyncio
    async def test_list_enrollments_unauthorized(self, client: AsyncClient):
        """Test listing enrollments without authentication."""
        response = await client.get("/api/v1/enrollments/")
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_enrollment_unauthorized(
        self, client: AsyncClient, sample_enrollment_data: dict
    ):
        """Test creating an enrollment without authentication."""
        response = await client.post(
            "/api/v1/enrollments/", json=sample_enrollment_data
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_enrollment_unauthorized(self, client: AsyncClient):
        """Test getting an enrollment without authentication."""
        response = await client.get("/api/v1/enrollments/1")
        assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_get_enrollment_stats_unauthorized(
        self, client: AsyncClient
    ):
        """Test getting enrollment stats without authentication."""
        response = await client.get("/api/v1/enrollments/stats")
        assert response.status_code in [401, 403]


class TestEnrollmentValidation:
    """Test input validation for enrollment endpoints."""

    @pytest.mark.asyncio
    async def test_create_enrollment_missing_course_id(
        self, client: AsyncClient
    ):
        """Test creating enrollment without course_id."""
        response = await client.post("/api/v1/enrollments/", json={})
        # Should return validation error or auth error
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_create_enrollment_invalid_course_id(
        self, client: AsyncClient
    ):
        """Test creating enrollment with invalid course_id."""
        response = await client.post(
            "/api/v1/enrollments/", json={"course_id": "invalid"}
        )
        assert response.status_code in [401, 422]


class TestEnrollmentStatus:
    """Test enrollment status management."""

    @pytest.mark.asyncio
    async def test_update_enrollment_unauthorized(
        self, client: AsyncClient, sample_progress_update: dict
    ):
        """Test updating enrollment progress without authentication."""
        response = await client.put(
            "/api/v1/enrollments/1", json=sample_progress_update
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_cancel_enrollment_unauthorized(self, client: AsyncClient):
        """Test cancelling an enrollment without authentication."""
        response = await client.delete("/api/v1/enrollments/1")
        assert response.status_code in [401, 403]


class TestCourseEnrollments:
    """Test course-specific enrollment endpoints."""

    @pytest.mark.asyncio
    async def test_get_course_enrollments_unauthorized(
        self, client: AsyncClient
    ):
        """Test getting enrollments for a course without authentication."""
        response = await client.get(
            "/api/v1/enrollments/courses/1/enrollments"
        )
        # This may be instructor-only endpoint
        assert response.status_code in [401, 403, 404]
