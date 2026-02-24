"""Payment repository for database operations."""

from decimal import Decimal
from typing import List, Optional

from app.models.payment import Payment, PaymentStatus
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class PaymentRepository:
    """Repository for Payment database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create_payment(self, payment_data: dict) -> Payment:
        """Create a new payment."""
        payment = Payment(**payment_data)
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_payment_by_id(self, payment_id: int) -> Optional[Payment]:
        """Get payment by ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_intent_id(
        self, intent_id: str
    ) -> Optional[Payment]:
        """Get payment by payment intent ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.payment_intent_id == intent_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_transaction_id(
        self, transaction_id: str
    ) -> Optional[Payment]:
        """Get payment by transaction ID."""
        result = await self.db.execute(
            select(Payment).where(Payment.transaction_id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[Payment]:
        """Get payment by idempotency key for duplicate prevention."""
        result = await self.db.execute(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def get_user_payments(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[PaymentStatus] = None,
    ) -> List[Payment]:
        """Get all payments for a user."""
        query = select(Payment).where(Payment.user_id == user_id)

        if status:
            query = query.where(Payment.status == status)

        query = (
            query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_payments(
        self, user_id: int, status: Optional[PaymentStatus] = None
    ) -> int:
        """Count user payments."""
        query = (
            select(func.count())
            .select_from(Payment)
            .where(Payment.user_id == user_id)
        )

        if status:
            query = query.where(Payment.status == status)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_course_payments(
        self,
        course_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[PaymentStatus] = None,
    ) -> List[Payment]:
        """Get all payments for a course."""
        query = select(Payment).where(Payment.course_id == course_id)

        if status:
            query = query.where(Payment.status == status)

        query = (
            query.order_by(Payment.created_at.desc()).offset(skip).limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_course_payments(
        self, course_id: int, status: Optional[PaymentStatus] = None
    ) -> int:
        """Count course payments."""
        query = (
            select(func.count())
            .select_from(Payment)
            .where(Payment.course_id == course_id)
        )

        if status:
            query = query.where(Payment.status == status)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_user_payment_for_course(
        self, user_id: int, course_id: int
    ) -> Optional[Payment]:
        """Get user's payment for a specific course (completed)."""
        result = await self.db.execute(
            select(Payment)
            .where(
                and_(
                    Payment.user_id == user_id,
                    Payment.course_id == course_id,
                    Payment.status == PaymentStatus.COMPLETED,
                )
            )
            .order_by(Payment.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def update_payment(self, payment: Payment) -> Payment:
        """Update payment."""
        await self.db.commit()
        await self.db.refresh(payment)
        return payment

    async def get_payment_stats(self, user_id: Optional[int] = None) -> dict:
        """Get payment statistics."""
        query = select(
            func.count().label("total"),
            func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label(
                "total_amount"
            ),
            func.count()
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .label("completed"),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.status == PaymentStatus.COMPLETED
                ),
                Decimal("0.00"),
            ).label("completed_amount"),
            func.count()
            .filter(Payment.status == PaymentStatus.PENDING)
            .label("pending"),
            func.count()
            .filter(Payment.status == PaymentStatus.FAILED)
            .label("failed"),
            func.count()
            .filter(Payment.status == PaymentStatus.REFUNDED)
            .label("refunded"),
            func.coalesce(
                func.sum(Payment.amount).filter(
                    Payment.status == PaymentStatus.REFUNDED
                ),
                Decimal("0.00"),
            ).label("refunded_amount"),
        ).select_from(Payment)

        if user_id:
            query = query.where(Payment.user_id == user_id)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_payments": row.total,
            "total_amount": row.total_amount,
            "completed_payments": row.completed,
            "completed_amount": row.completed_amount,
            "pending_payments": row.pending,
            "failed_payments": row.failed,
            "refunded_payments": row.refunded,
            "refunded_amount": row.refunded_amount,
        }
