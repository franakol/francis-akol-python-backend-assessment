"""Payment service with transaction handling."""

import math
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx
from app.core.config import settings
from app.core.payment_gateway import payment_gateway
from app.models.payment import Payment, PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import (
    PaginatedPaymentResponse,
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentResponse,
    PaymentStatsResponse,
)
from fastapi import HTTPException, status


class PaymentService:
    """Service for payment operations with transaction handling."""

    def __init__(self, payment_repository: PaymentRepository):
        """Initialize payment service with repository."""
        self.payment_repository = payment_repository

    async def create_payment_intent(
        self, payment_data: PaymentIntentCreate, user_id: int
    ) -> PaymentIntentResponse:
        """
        Create a payment intent for course enrollment.

        Steps:
        1. Check idempotency key for existing payment (prevents duplicates)
        2. Verify course exists and get price
        3. Check if user already paid for this course
        4. Create payment intent via payment gateway
        5. Store payment record in database

        Args:
            payment_data: Payment intent creation data
            user_id: User ID creating the payment

        Returns:
            Payment intent response with client_secret

        Raises:
            HTTPException: If course not found or already paid
        """
        # Check idempotency key for existing payment (prevents duplicates)
        if payment_data.idempotency_key:
            existing_payment = (
                await self.payment_repository.get_payment_by_idempotency_key(
                    payment_data.idempotency_key
                )
            )
            if existing_payment:
                # Return existing payment instead of creating duplicate
                return PaymentIntentResponse(
                    payment_id=existing_payment.id,
                    payment_intent_id=existing_payment.payment_intent_id or "",
                    amount=existing_payment.amount,
                    currency=existing_payment.currency,
                    status=existing_payment.status,
                    client_secret=None,  # Client secret only available on first creation
                )

        # Get course details from Course Service
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.COURSE_SERVICE_URL}/api/v1/courses/{payment_data.course_id}",
                    timeout=10.0,
                )

                if response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Course not found",
                    )

                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Failed to retrieve course information",
                    )

                course = response.json()
                course_price = Decimal(str(course.get("price", 0)))

                if course_price <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Course is free, no payment required",
                    )

        except httpx.RequestError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Course service unavailable",
            )

        # Check if user already paid for this course
        existing_payment = (
            await self.payment_repository.get_user_payment_for_course(
                user_id, payment_data.course_id
            )
        )

        if existing_payment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already paid for this course",
            )

        # Create payment intent via gateway
        intent = await payment_gateway.create_payment_intent(
            amount=course_price,
            currency=payment_data.currency,
            metadata={
                "user_id": user_id,
                "course_id": payment_data.course_id,
            },
        )

        # Create payment record
        payment = await self.payment_repository.create_payment(
            {
                "user_id": user_id,
                "course_id": payment_data.course_id,
                "amount": course_price,
                "currency": payment_data.currency,
                "status": PaymentStatus.PENDING,
                "payment_method": payment_data.payment_method,
                "payment_intent_id": intent["id"],
                "idempotency_key": payment_data.idempotency_key,
            }
        )

        return PaymentIntentResponse(
            payment_id=payment.id,
            payment_intent_id=intent["id"],
            amount=course_price,
            currency=payment_data.currency,
            status=PaymentStatus.PENDING,
            client_secret=intent.get("client_secret"),
        )

    async def confirm_payment(
        self, payment_id: int, payment_intent_id: str, user_id: int
    ) -> PaymentResponse:
        """
        Confirm payment after user completes payment on client side.

        Steps:
        1. Verify payment exists and belongs to user
        2. Confirm payment intent with gateway
        3. Update payment status
        4. Create enrollment if successful

        Args:
            payment_id: Payment ID
            payment_intent_id: Payment intent ID from gateway
            user_id: User ID confirming the payment

        Returns:
            Updated payment response

        Raises:
            HTTPException: If payment not found or unauthorized
        """
        payment = await self.payment_repository.get_payment_by_id(payment_id)

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        if payment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to confirm this payment",
            )

        if payment.status != PaymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment already {payment.status.value}",
            )

        # Confirm with payment gateway
        try:
            result = await payment_gateway.confirm_payment_intent(
                payment_intent_id
            )

            if result["status"] == "succeeded":
                payment.status = PaymentStatus.COMPLETED
                payment.transaction_id = result.get(
                    "transaction_id"
                ) or result.get("charges", {}).get("data", [{}])[0].get("id")

                # Create enrollment after successful payment
                await self._create_enrollment_for_payment(payment)
            else:
                payment.status = PaymentStatus.FAILED
                payment.failure_reason = result.get(
                    "failure_message", "Payment failed"
                )

        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.failure_reason = str(e)

        payment = await self.payment_repository.update_payment(payment)

        return PaymentResponse.model_validate(payment)

    async def _create_enrollment_for_payment(self, payment: Payment) -> None:
        """Create enrollment after successful payment."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.ENROLLMENT_SERVICE_URL}/api/v1/enrollments/",
                    json={"course_id": payment.course_id},
                    headers={"x-user-id": str(payment.user_id)},
                    timeout=10.0,
                )

                if response.status_code == 201:
                    enrollment_data = response.json()
                    payment.enrollment_id = enrollment_data.get("id")
                    await self.payment_repository.update_payment(payment)

        except Exception:
            # Log error but don't fail payment
            # Enrollment can be created manually if needed
            pass

    async def get_payment_by_id(
        self, payment_id: int, user_id: int
    ) -> PaymentResponse:
        """Get payment by ID."""
        payment = await self.payment_repository.get_payment_by_id(payment_id)

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        # Check if user owns this payment
        if payment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this payment",
            )

        return PaymentResponse.model_validate(payment)

    async def get_user_payments(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        status_filter: Optional[PaymentStatus] = None,
    ) -> PaginatedPaymentResponse:
        """Get paginated list of user payments."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        skip = (page - 1) * page_size

        # Get payments and total count
        payments = await self.payment_repository.get_user_payments(
            user_id, skip=skip, limit=page_size, status=status_filter
        )
        total = await self.payment_repository.count_user_payments(
            user_id, status=status_filter
        )

        # Calculate total pages
        total_pages = math.ceil(total / page_size)

        return PaginatedPaymentResponse(
            items=[PaymentResponse.model_validate(p) for p in payments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def refund_payment(
        self, payment_id: int, reason: Optional[str], is_admin: bool = False
    ) -> PaymentResponse:
        """
        Refund a payment (admin only).

        Args:
            payment_id: Payment ID to refund
            reason: Refund reason
            is_admin: Whether user is admin

        Returns:
            Updated payment response

        Raises:
            HTTPException: If not authorized or payment cannot be refunded
        """
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can refund payments",
            )

        payment = await self.payment_repository.get_payment_by_id(payment_id)

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found",
            )

        if payment.status != PaymentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only refund completed payments",
            )

        # Process refund via gateway
        try:
            await payment_gateway.refund_payment(
                payment.transaction_id, reason
            )

            payment.status = PaymentStatus.REFUNDED
            payment.refund_reason = reason
            payment.refunded_at = datetime.utcnow()

            payment = await self.payment_repository.update_payment(payment)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Refund failed: {str(e)}",
            )

        return PaymentResponse.model_validate(payment)

    async def get_payment_stats(self, user_id: int) -> PaymentStatsResponse:
        """Get payment statistics for a user."""
        stats = await self.payment_repository.get_payment_stats(user_id)
        return PaymentStatsResponse(**stats)
