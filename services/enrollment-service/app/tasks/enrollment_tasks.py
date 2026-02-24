"""Celery tasks for enrollment processing."""

import httpx
from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import async_session
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.repositories.enrollment_repository import EnrollmentRepository


@celery_app.task(name="process_enrollment")
def process_enrollment(enrollment_id: int) -> dict:
    """
    Process enrollment asynchronously.

    - Verify course availability
    - Check max students quota
    - Activate enrollment
    - Update course enrolled count
    - Send notification (placeholder)
    """
    import asyncio

    async def _process():
        async with async_session() as db:
            repository = EnrollmentRepository(db)
            enrollment = await repository.get_enrollment_by_id(enrollment_id)

            if not enrollment:
                return {"status": "error", "message": "Enrollment not found"}

            if enrollment.status != EnrollmentStatus.PENDING:
                return {
                    "status": "error",
                    "message": "Enrollment already processed",
                }

            try:
                # Check course availability and quota
                async with httpx.AsyncClient() as client:
                    # Get course details
                    course_response = await client.get(
                        f"{settings.COURSE_SERVICE_URL}/api/v1/courses/{enrollment.course_id}",
                        timeout=10.0,
                    )

                    if course_response.status_code != 200:
                        enrollment.status = EnrollmentStatus.CANCELLED
                        await repository.update_enrollment(enrollment)
                        return {
                            "status": "error",
                            "message": "Course not found",
                        }

                    course = course_response.json()

                    # Check if course is published
                    if not course.get("is_published"):
                        enrollment.status = EnrollmentStatus.CANCELLED
                        await repository.update_enrollment(enrollment)
                        return {
                            "status": "error",
                            "message": "Course not published",
                        }

                    # Check max students quota
                    max_students = course.get("max_students")
                    if (
                        max_students
                        and course.get("enrolled_count", 0) >= max_students
                    ):
                        enrollment.status = EnrollmentStatus.CANCELLED
                        await repository.update_enrollment(enrollment)
                        return {"status": "error", "message": "Course is full"}

                # Activate enrollment
                enrollment.status = EnrollmentStatus.ACTIVE
                await repository.update_enrollment(enrollment)

                # TODO: Send enrollment confirmation notification
                # TODO: Update course enrolled count via API or event

                return {
                    "status": "success",
                    "message": "Enrollment activated",
                    "enrollment_id": enrollment_id,
                }

            except Exception as e:
                # Rollback to pending or cancel on error
                enrollment.status = EnrollmentStatus.CANCELLED
                await repository.update_enrollment(enrollment)
                return {"status": "error", "message": str(e)}

    return asyncio.run(_process())


@celery_app.task(name="update_enrollment_progress")
def update_enrollment_progress(enrollment_id: int, progress: int) -> dict:
    """
    Update enrollment progress asynchronously.

    - Update progress percentage
    - Check if course completed (100%)
    - Send completion notification if needed
    """
    import asyncio
    from datetime import datetime

    async def _update():
        async with async_session() as db:
            repository = EnrollmentRepository(db)
            enrollment = await repository.get_enrollment_by_id(enrollment_id)

            if not enrollment:
                return {"status": "error", "message": "Enrollment not found"}

            # Update progress
            enrollment.progress_percentage = min(max(progress, 0), 100)
            enrollment.last_accessed_at = datetime.utcnow()

            # Mark as completed if 100%
            if (
                enrollment.progress_percentage == 100
                and enrollment.status == EnrollmentStatus.ACTIVE
            ):
                enrollment.status = EnrollmentStatus.COMPLETED
                enrollment.completed_at = datetime.utcnow()
                # TODO: Send completion certificate/notification

            await repository.update_enrollment(enrollment)

            return {
                "status": "success",
                "enrollment_id": enrollment_id,
                "progress": enrollment.progress_percentage,
            }

    return asyncio.run(_update())


@celery_app.task(name="cancel_expired_pending_enrollments")
def cancel_expired_pending_enrollments() -> dict:
    """
    Cancel pending enrollments older than 24 hours (scheduled task).
    """
    import asyncio
    from datetime import datetime, timedelta

    from sqlalchemy import and_, select

    async def _cancel():
        async with async_session() as db:
            repository = EnrollmentRepository(db)

            # Find pending enrollments older than 24 hours
            expiry_time = datetime.utcnow() - timedelta(hours=24)

            result = await db.execute(
                select(Enrollment).where(
                    and_(
                        Enrollment.status == EnrollmentStatus.PENDING,
                        Enrollment.created_at < expiry_time,
                    )
                )
            )
            expired_enrollments = result.scalars().all()

            cancelled_count = 0
            for enrollment in expired_enrollments:
                enrollment.status = EnrollmentStatus.CANCELLED
                await repository.update_enrollment(enrollment)
                cancelled_count += 1

            return {"status": "success", "cancelled_count": cancelled_count}

    return asyncio.run(_cancel())
