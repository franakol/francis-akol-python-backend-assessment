"""Enrollment service with async processing."""

import math
from datetime import datetime
from typing import Optional

from app.models.enrollment import EnrollmentStatus
from app.repositories.enrollment_repository import EnrollmentRepository
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentStatsResponse,
    EnrollmentUpdate,
    PaginatedEnrollmentResponse,
)
from app.tasks.enrollment_tasks import (
    process_enrollment,
    update_enrollment_progress,
)
from fastapi import HTTPException, status


class EnrollmentService:
    """Service for enrollment operations with async processing."""

    def __init__(self, enrollment_repository: EnrollmentRepository):
        """Initialize enrollment service with repository."""
        self.enrollment_repository = enrollment_repository

    async def create_enrollment(
        self, enrollment_data: EnrollmentCreate, user_id: int
    ) -> EnrollmentResponse:
        """
        Create a new enrollment and process it asynchronously.

        Args:
            enrollment_data: Enrollment creation data
            user_id: User ID creating the enrollment

        Returns:
            Enrollment response

        Raises:
            HTTPException: If already enrolled
        """
        # Check if user is already enrolled in this course
        existing = (
            await self.enrollment_repository.get_user_enrollment_for_course(
                user_id, enrollment_data.course_id
            )
        )

        if existing and existing.status in [
            EnrollmentStatus.ACTIVE,
            EnrollmentStatus.PENDING,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already enrolled in this course",
            )

        # Create enrollment with pending status
        enrollment = await self.enrollment_repository.create_enrollment(
            user_id, enrollment_data.course_id
        )

        # Trigger async processing
        process_enrollment.delay(enrollment.id)

        return EnrollmentResponse.model_validate(enrollment)

    async def get_enrollment_by_id(
        self, enrollment_id: int, user_id: int
    ) -> EnrollmentResponse:
        """Get enrollment by ID."""
        enrollment = await self.enrollment_repository.get_enrollment_by_id(
            enrollment_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Check if user owns this enrollment
        if enrollment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this enrollment",
            )

        return EnrollmentResponse.model_validate(enrollment)

    async def get_user_enrollments(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
        status_filter: Optional[EnrollmentStatus] = None,
    ) -> PaginatedEnrollmentResponse:
        """Get paginated list of user enrollments."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        skip = (page - 1) * page_size

        # Get enrollments and total count
        enrollments = await self.enrollment_repository.get_user_enrollments(
            user_id, skip=skip, limit=page_size, status=status_filter
        )
        total = await self.enrollment_repository.count_user_enrollments(
            user_id, status=status_filter
        )

        # Calculate total pages
        total_pages = math.ceil(total / page_size)

        return PaginatedEnrollmentResponse(
            items=[EnrollmentResponse.model_validate(e) for e in enrollments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def update_enrollment(
        self,
        enrollment_id: int,
        enrollment_data: EnrollmentUpdate,
        user_id: int,
    ) -> EnrollmentResponse:
        """Update enrollment."""
        enrollment = await self.enrollment_repository.get_enrollment_by_id(
            enrollment_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Check if user owns this enrollment
        if enrollment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this enrollment",
            )

        # Update fields
        update_dict = enrollment_data.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            if key == "status" and value == EnrollmentStatus.COMPLETED:
                enrollment.completed_at = datetime.utcnow()
            setattr(enrollment, key, value)

        enrollment = await self.enrollment_repository.update_enrollment(
            enrollment
        )

        # If progress updated, trigger async task
        if "progress_percentage" in update_dict:
            update_enrollment_progress.delay(
                enrollment.id, enrollment.progress_percentage
            )

        return EnrollmentResponse.model_validate(enrollment)

    async def cancel_enrollment(
        self, enrollment_id: int, user_id: int
    ) -> None:
        """Cancel enrollment."""
        enrollment = await self.enrollment_repository.get_enrollment_by_id(
            enrollment_id
        )

        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Enrollment not found",
            )

        # Check if user owns this enrollment
        if enrollment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to cancel this enrollment",
            )

        # Can only cancel if not completed
        if enrollment.status == EnrollmentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel completed enrollment",
            )

        enrollment.status = EnrollmentStatus.CANCELLED
        await self.enrollment_repository.update_enrollment(enrollment)

    async def get_course_enrollments(
        self,
        course_id: int,
        instructor_id: int,
        page: int = 1,
        page_size: int = 10,
        status_filter: Optional[EnrollmentStatus] = None,
    ) -> PaginatedEnrollmentResponse:
        """Get enrollments for a course (instructor only)."""
        # TODO: Verify instructor owns the course via Course Service

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        skip = (page - 1) * page_size

        # Get enrollments and total count
        enrollments = await self.enrollment_repository.get_course_enrollments(
            course_id, skip=skip, limit=page_size, status=status_filter
        )
        total = await self.enrollment_repository.count_course_enrollments(
            course_id, status=status_filter
        )

        # Calculate total pages
        total_pages = math.ceil(total / page_size)

        return PaginatedEnrollmentResponse(
            items=[EnrollmentResponse.model_validate(e) for e in enrollments],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_enrollment_stats(
        self, user_id: int
    ) -> EnrollmentStatsResponse:
        """Get enrollment statistics for a user."""
        stats = await self.enrollment_repository.get_enrollment_stats(user_id)
        return EnrollmentStatsResponse(**stats)
