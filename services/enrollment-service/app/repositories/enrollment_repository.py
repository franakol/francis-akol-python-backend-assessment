"""Enrollment repository for database operations."""

from typing import List, Optional

from app.models.enrollment import Enrollment, EnrollmentStatus
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class EnrollmentRepository:
    """Repository for Enrollment database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    async def create_enrollment(
        self, user_id: int, course_id: int
    ) -> Enrollment:
        """Create a new enrollment."""
        enrollment = Enrollment(
            user_id=user_id,
            course_id=course_id,
            status=EnrollmentStatus.PENDING,
        )
        self.db.add(enrollment)
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def get_enrollment_by_id(
        self, enrollment_id: int
    ) -> Optional[Enrollment]:
        """Get enrollment by ID."""
        result = await self.db.execute(
            select(Enrollment).where(Enrollment.id == enrollment_id)
        )
        return result.scalar_one_or_none()

    async def get_user_enrollment_for_course(
        self, user_id: int, course_id: int
    ) -> Optional[Enrollment]:
        """Get user's enrollment for a specific course."""
        result = await self.db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.user_id == user_id,
                    Enrollment.course_id == course_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_user_enrollments(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[EnrollmentStatus] = None,
    ) -> List[Enrollment]:
        """Get all enrollments for a user."""
        query = select(Enrollment).where(Enrollment.user_id == user_id)

        if status:
            query = query.where(Enrollment.status == status)

        query = (
            query.order_by(Enrollment.enrolled_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_user_enrollments(
        self, user_id: int, status: Optional[EnrollmentStatus] = None
    ) -> int:
        """Count user enrollments."""
        query = (
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.user_id == user_id)
        )

        if status:
            query = query.where(Enrollment.status == status)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_course_enrollments(
        self,
        course_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[EnrollmentStatus] = None,
    ) -> List[Enrollment]:
        """Get all enrollments for a course."""
        query = select(Enrollment).where(Enrollment.course_id == course_id)

        if status:
            query = query.where(Enrollment.status == status)

        query = (
            query.order_by(Enrollment.enrolled_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_course_enrollments(
        self, course_id: int, status: Optional[EnrollmentStatus] = None
    ) -> int:
        """Count course enrollments."""
        query = (
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.course_id == course_id)
        )

        if status:
            query = query.where(Enrollment.status == status)

        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_enrollment(self, enrollment: Enrollment) -> Enrollment:
        """Update enrollment."""
        await self.db.commit()
        await self.db.refresh(enrollment)
        return enrollment

    async def delete_enrollment(self, enrollment: Enrollment) -> None:
        """Delete enrollment."""
        await self.db.delete(enrollment)
        await self.db.commit()

    async def get_enrollment_stats(
        self, user_id: Optional[int] = None
    ) -> dict:
        """Get enrollment statistics."""
        query = select(
            func.count().label("total"),
            func.count()
            .filter(Enrollment.status == EnrollmentStatus.ACTIVE)
            .label("active"),
            func.count()
            .filter(Enrollment.status == EnrollmentStatus.COMPLETED)
            .label("completed"),
            func.count()
            .filter(Enrollment.status == EnrollmentStatus.CANCELLED)
            .label("cancelled"),
            func.count()
            .filter(Enrollment.status == EnrollmentStatus.PENDING)
            .label("pending"),
        ).select_from(Enrollment)

        if user_id:
            query = query.where(Enrollment.user_id == user_id)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_enrollments": row.total,
            "active_enrollments": row.active,
            "completed_enrollments": row.completed,
            "cancelled_enrollments": row.cancelled,
            "pending_enrollments": row.pending,
        }
