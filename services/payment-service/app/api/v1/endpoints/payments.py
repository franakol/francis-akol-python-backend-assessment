"""Payment endpoints."""

from typing import Optional

from app.core.dependencies import get_db
from app.models.payment import PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import (
    PaginatedPaymentResponse,
    PaymentConfirm,
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentRefund,
    PaymentResponse,
    PaymentStatsResponse,
)
from app.services.payment_service import PaymentService
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_intent(
    payment_data: PaymentIntentCreate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create payment intent for course enrollment.

    Steps:
    1. Retrieves course price from Course Service
    2. Validates user hasn't already paid
    3. Creates payment intent via payment gateway
    4. Returns client_secret for frontend payment form

    - **course_id**: Course ID to purchase
    - **payment_method**: Payment method (credit_card, paypal, etc.)
    - **currency**: Currency code (default: USD)
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.create_payment_intent(payment_data, x_user_id)


@router.post("/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_payment(
    payment_id: int,
    confirm_data: PaymentConfirm,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm payment after client-side processing.

    After user completes payment on frontend:
    1. Confirms payment with gateway
    2. Updates payment status (COMPLETED or FAILED)
    3. Creates enrollment if successful

    - **payment_id**: Payment ID to confirm
    - **payment_intent_id**: Payment intent ID from gateway
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.confirm_payment(
        payment_id, confirm_data.payment_intent_id, x_user_id
    )


@router.get("/", response_model=PaginatedPaymentResponse)
async def get_user_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[PaymentStatus] = Query(None),
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's payments (paginated).

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (PENDING, COMPLETED, FAILED, REFUNDED)
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.get_user_payments(
        x_user_id, page=page, page_size=page_size, status_filter=status_filter
    )


@router.get("/stats", response_model=PaymentStatsResponse)
async def get_payment_stats(
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment statistics for current user.

    Returns:
    - Total payments and amount
    - Completed/Pending/Failed/Refunded counts
    - Total amounts by status
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.get_payment_stats(x_user_id)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: int,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment by ID.

    - **payment_id**: Payment ID
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.get_payment_by_id(payment_id, x_user_id)


@router.post("/{payment_id}/refund", response_model=PaymentResponse)
async def refund_payment(
    payment_id: int,
    refund_data: PaymentRefund,
    x_is_admin: bool = Header(False, description="Is admin user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Refund a payment (admin only).

    Processes refund via payment gateway and updates status.

    - **payment_id**: Payment ID to refund
    - **reason**: Refund reason (optional)
    """
    payment_repository = PaymentRepository(db)
    payment_service = PaymentService(payment_repository)
    return await payment_service.refund_payment(
        payment_id, refund_data.reason, x_is_admin
    )
