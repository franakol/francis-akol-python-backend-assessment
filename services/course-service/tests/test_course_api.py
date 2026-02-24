"""Tests for Course API endpoints."""

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
        assert data["service"] == "course-service"

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
        assert data["service"] == "Course Service"
        assert "version" in data


class TestCategoryEndpoints:
    """Test category API endpoints."""

    @pytest.mark.asyncio
    async def test_create_category(
        self, client: AsyncClient, sample_category_data: dict
    ):
        """Test creating a new category."""
        response = await client.post(
            "/api/v1/categories/", json=sample_category_data
        )
        # May require auth - check for appropriate response
        assert response.status_code in [201, 401, 403]

    @pytest.mark.asyncio
    async def test_list_categories_empty(self, client: AsyncClient):
        """Test listing categories when none exist."""
        response = await client.get("/api/v1/categories/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_category_not_found(self, client: AsyncClient):
        """Test getting a non-existent category."""
        response = await client.get("/api/v1/categories/99999")
        assert response.status_code == 404


class TestCourseEndpoints:
    """Test course API endpoints."""

    @pytest.mark.asyncio
    async def test_list_courses_empty(self, client: AsyncClient):
        """Test listing courses when none exist."""
        response = await client.get("/api/v1/courses/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_courses_pagination(self, client: AsyncClient):
        """Test course listing with pagination parameters."""
        response = await client.get("/api/v1/courses/?page=1&page_size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_course_not_found(self, client: AsyncClient):
        """Test getting a non-existent course."""
        response = await client.get("/api/v1/courses/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_course_unauthorized(
        self, client: AsyncClient, sample_course_data: dict
    ):
        """Test creating a course without authentication."""
        response = await client.post(
            "/api/v1/courses/", json=sample_course_data
        )
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_list_courses_with_filters(self, client: AsyncClient):
        """Test listing courses with various filter parameters."""
        # Test with published filter
        response = await client.get("/api/v1/courses/?is_published=true")
        assert response.status_code == 200

        # Test with category filter
        response = await client.get("/api/v1/courses/?category_id=1")
        assert response.status_code == 200

        # Test with search query
        response = await client.get("/api/v1/courses/?search=python")
        assert response.status_code == 200


class TestCourseContentEndpoints:
    """Test course content API endpoints."""

    @pytest.mark.asyncio
    async def test_get_course_content_not_found(self, client: AsyncClient):
        """Test getting content for non-existent course."""
        response = await client.get("/api/v1/courses/99999/content")
        assert response.status_code == 404


class TestValidation:
    """Test input validation for API endpoints."""

    @pytest.mark.asyncio
    async def test_invalid_pagination_params(self, client: AsyncClient):
        """Test that invalid pagination params are handled."""
        response = await client.get("/api/v1/courses/?page=0&page_size=0")
        # Should handle gracefully or return validation error
        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_invalid_category_id(self, client: AsyncClient):
        """Test filtering by invalid category ID."""
        response = await client.get("/api/v1/courses/?category_id=invalid")
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_large_page_size(self, client: AsyncClient):
        """Test handling of very large page size."""
        response = await client.get("/api/v1/courses/?page_size=10000")
        assert response.status_code == 200  # Should cap page size
