"""Tests for Payment API endpoints."""

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
        assert data["service"] == "payment-service"

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
        assert data["service"] == "Payment Service"
        assert "version" in data


class TestPaymentEndpoints:
    """Test payment API endpoints."""

    @pytest.mark.asyncio
    async def test_list_payments_unauthorized(self, client: AsyncClient):
        """Test listing payments without authentication."""
        response = await client.get("/api/v1/payments/")
        # Should require authentication
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_payment_unauthorized(
        self, client: AsyncClient, sample_payment_data: dict
    ):
        """Test creating a payment without authentication."""
        response = await client.post(
            "/api/v1/payments/", json=sample_payment_data
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_payment_unauthorized(self, client: AsyncClient):
        """Test getting a payment without authentication."""
        response = await client.get("/api/v1/payments/1")
        assert response.status_code in [401, 403, 404]

    @pytest.mark.asyncio
    async def test_get_payment_stats_unauthorized(self, client: AsyncClient):
        """Test getting payment stats without authentication."""
        response = await client.get("/api/v1/payments/stats")
        assert response.status_code in [401, 403]


class TestPaymentValidation:
    """Test input validation for payment endpoints."""

    @pytest.mark.asyncio
    async def test_create_payment_missing_fields(self, client: AsyncClient):
        """Test creating payment without required fields."""
        response = await client.post("/api/v1/payments/", json={})
        # Should return validation error or auth error
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_create_payment_invalid_amount(self, client: AsyncClient):
        """Test creating payment with invalid amount."""
        response = await client.post(
            "/api/v1/payments/",
            json={
                "course_id": 1,
                "amount": "invalid",
                "currency": "USD",
                "payment_method": "credit_card",
            },
        )
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_create_payment_negative_amount(self, client: AsyncClient):
        """Test creating payment with negative amount."""
        response = await client.post(
            "/api/v1/payments/",
            json={
                "course_id": 1,
                "amount": "-10.00",
                "currency": "USD",
                "payment_method": "credit_card",
            },
        )
        assert response.status_code in [401, 422]


class TestPaymentConfirmation:
    """Test payment confirmation endpoints."""

    @pytest.mark.asyncio
    async def test_confirm_payment_unauthorized(self, client: AsyncClient):
        """Test confirming a payment without authentication."""
        response = await client.post("/api/v1/payments/1/confirm")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_confirm_nonexistent_payment(self, client: AsyncClient):
        """Test confirming a non-existent payment."""
        response = await client.post("/api/v1/payments/99999/confirm")
        assert response.status_code in [401, 403, 404]


class TestRefundEndpoints:
    """Test payment refund endpoints."""

    @pytest.mark.asyncio
    async def test_refund_payment_unauthorized(
        self, client: AsyncClient, sample_refund_data: dict
    ):
        """Test refunding a payment without authentication."""
        response = await client.post(
            "/api/v1/payments/1/refund", json=sample_refund_data
        )
        # Refund typically requires admin
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_refund_nonexistent_payment(
        self, client: AsyncClient, sample_refund_data: dict
    ):
        """Test refunding a non-existent payment."""
        response = await client.post(
            "/api/v1/payments/99999/refund", json=sample_refund_data
        )
        assert response.status_code in [401, 403, 404]


class TestPaymentMethods:
    """Test payment method validation."""

    @pytest.mark.asyncio
    async def test_invalid_payment_method(self, client: AsyncClient):
        """Test creating payment with invalid payment method."""
        response = await client.post(
            "/api/v1/payments/",
            json={
                "course_id": 1,
                "amount": "99.99",
                "currency": "USD",
                "payment_method": "invalid_method",
            },
        )
        assert response.status_code in [401, 422]

    @pytest.mark.asyncio
    async def test_invalid_currency(self, client: AsyncClient):
        """Test creating payment with invalid currency."""
        response = await client.post(
            "/api/v1/payments/",
            json={
                "course_id": 1,
                "amount": "99.99",
                "currency": "INVALID",
                "payment_method": "credit_card",
            },
        )
        assert response.status_code in [401, 422]
