"""Tests for payment idempotency functionality."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentIntentCreate
from app.services.payment_service import PaymentService


class TestIdempotencyKey:
    """Test idempotency key functionality."""

    @pytest.mark.asyncio
    async def test_payment_model_has_idempotency_key_field(self):
        """Test that Payment model has idempotency_key field."""
        # Create a payment instance with idempotency key
        payment = Payment(
            user_id=1,
            course_id=1,
            amount=Decimal("99.99"),
            currency="USD",
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.CREDIT_CARD,
            idempotency_key="test-unique-key-123",
        )
        assert payment.idempotency_key == "test-unique-key-123"

    @pytest.mark.asyncio
    async def test_payment_model_idempotency_key_can_be_none(self):
        """Test that idempotency_key can be None for backwards compatibility."""
        payment = Payment(
            user_id=1,
            course_id=1,
            amount=Decimal("99.99"),
            currency="USD",
            status=PaymentStatus.PENDING,
            payment_method=PaymentMethod.CREDIT_CARD,
        )
        assert payment.idempotency_key is None


class TestPaymentIntentCreateSchema:
    """Test PaymentIntentCreate schema with idempotency key."""

    def test_schema_accepts_idempotency_key(self):
        """Test that schema accepts idempotency_key field."""
        data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
            idempotency_key="unique-key-456",
        )
        assert data.idempotency_key == "unique-key-456"

    def test_schema_idempotency_key_optional(self):
        """Test that idempotency_key is optional."""
        data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
        )
        assert data.idempotency_key is None

    def test_schema_idempotency_key_max_length(self):
        """Test that idempotency_key respects max length of 255."""
        # This should work (255 chars)
        key_255 = "a" * 255
        data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
            idempotency_key=key_255,
        )
        assert len(data.idempotency_key) == 255


class TestPaymentRepositoryIdempotency:
    """Test payment repository idempotency methods."""

    @pytest.mark.asyncio
    async def test_get_payment_by_idempotency_key_found(self, db_session):
        """Test finding payment by idempotency key."""
        repo = PaymentRepository(db_session)

        # Create a payment with idempotency key
        payment_data = {
            "user_id": 1,
            "course_id": 1,
            "amount": Decimal("99.99"),
            "currency": "USD",
            "status": PaymentStatus.PENDING,
            "payment_method": PaymentMethod.CREDIT_CARD,
            "idempotency_key": "repo-test-key-123",
        }
        created_payment = await repo.create_payment(payment_data)

        # Find by idempotency key
        found_payment = await repo.get_payment_by_idempotency_key(
            "repo-test-key-123"
        )

        assert found_payment is not None
        assert found_payment.id == created_payment.id
        assert found_payment.idempotency_key == "repo-test-key-123"

    @pytest.mark.asyncio
    async def test_get_payment_by_idempotency_key_not_found(self, db_session):
        """Test that None is returned when idempotency key doesn't exist."""
        repo = PaymentRepository(db_session)

        result = await repo.get_payment_by_idempotency_key("non-existent-key")
        assert result is None


class TestPaymentServiceIdempotency:
    """Test payment service idempotency handling."""

    @pytest.mark.asyncio
    async def test_duplicate_request_returns_existing_payment(self):
        """Test that duplicate request with same idempotency key returns existing payment."""
        # Mock repository
        mock_repo = AsyncMock(spec=PaymentRepository)

        # Create an existing payment that will be returned
        existing_payment = MagicMock()
        existing_payment.id = 42
        existing_payment.payment_intent_id = "pi_existing_123"
        existing_payment.amount = Decimal("99.99")
        existing_payment.currency = "USD"
        existing_payment.status = PaymentStatus.PENDING

        # First call to get_payment_by_idempotency_key returns existing payment
        mock_repo.get_payment_by_idempotency_key.return_value = (
            existing_payment
        )

        service = PaymentService(mock_repo)

        payment_data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
            idempotency_key="duplicate-key-123",
        )

        result = await service.create_payment_intent(payment_data, user_id=1)

        # Should return existing payment info
        assert result.payment_id == 42
        assert result.payment_intent_id == "pi_existing_123"
        assert (
            result.client_secret is None
        )  # Not available for existing payments

        # Should NOT call other repository methods or payment gateway
        mock_repo.get_user_payment_for_course.assert_not_called()
        mock_repo.create_payment.assert_not_called()

    @pytest.mark.asyncio
    async def test_new_request_with_idempotency_key_creates_payment(self):
        """Test that new request with unique idempotency key creates payment."""
        # Mock repository
        mock_repo = AsyncMock(spec=PaymentRepository)
        mock_repo.get_payment_by_idempotency_key.return_value = None
        mock_repo.get_user_payment_for_course.return_value = None

        # Mock created payment
        new_payment = MagicMock()
        new_payment.id = 100
        mock_repo.create_payment.return_value = new_payment

        service = PaymentService(mock_repo)

        payment_data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
            idempotency_key="new-unique-key-789",
        )

        # Mock external service calls
        with patch(
            "app.services.payment_service.httpx.AsyncClient"
        ) as mock_client, patch(
            "app.services.payment_service.payment_gateway"
        ) as mock_gateway:

            # Mock course service response
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 1,
                "price": "99.99",
                "title": "Test",
            }
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            # Mock payment gateway
            mock_gateway.create_payment_intent.return_value = {
                "id": "pi_new_123",
                "client_secret": "cs_secret_abc",
            }

            result = await service.create_payment_intent(
                payment_data, user_id=1
            )

            assert result.payment_id == 100

            # Verify idempotency key was included in payment creation
            create_call_args = mock_repo.create_payment.call_args[0][0]
            assert create_call_args["idempotency_key"] == "new-unique-key-789"

    @pytest.mark.asyncio
    async def test_request_without_idempotency_key_still_works(self):
        """Test that requests without idempotency key still work normally."""
        mock_repo = AsyncMock(spec=PaymentRepository)
        mock_repo.get_user_payment_for_course.return_value = None

        new_payment = MagicMock()
        new_payment.id = 200
        mock_repo.create_payment.return_value = new_payment

        service = PaymentService(mock_repo)

        # Request without idempotency key
        payment_data = PaymentIntentCreate(
            course_id=1,
            payment_method=PaymentMethod.CREDIT_CARD,
            currency="USD",
        )

        with patch(
            "app.services.payment_service.httpx.AsyncClient"
        ) as mock_client, patch(
            "app.services.payment_service.payment_gateway"
        ) as mock_gateway:

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": 1,
                "price": "50.00",
                "title": "Course",
            }
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            mock_gateway.create_payment_intent.return_value = {
                "id": "pi_no_idem_123",
                "client_secret": "cs_secret_xyz",
            }

            result = await service.create_payment_intent(
                payment_data, user_id=1
            )

            # Should NOT check idempotency key (because it's None)
            mock_repo.get_payment_by_idempotency_key.assert_not_called()

            # But should still create payment
            assert result.payment_id == 200
