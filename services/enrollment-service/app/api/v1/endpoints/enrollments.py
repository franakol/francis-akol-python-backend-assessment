"""Enrollment endpoints."""

from typing import Optional

from app.core.dependencies import get_db
from app.models.enrollment import EnrollmentStatus
from app.repositories.enrollment_repository import EnrollmentRepository
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentStatsResponse,
    EnrollmentUpdate,
    MessageResponse,
    PaginatedEnrollmentResponse,
)
from app.services.enrollment_service import EnrollmentService
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_enrollment(
    enrollment_data: EnrollmentCreate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll in a course (student).

    Creates enrollment with PENDING status and triggers async processing:
    - Checks course availability
    - Validates max students quota
    - Activates enrollment if successful

    - **course_id**: Course ID to enroll in
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.create_enrollment(
        enrollment_data, x_user_id
    )


@router.get("/", response_model=PaginatedEnrollmentResponse)
async def get_user_enrollments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[EnrollmentStatus] = Query(None),
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user's enrollments (paginated).

    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status (PENDING, ACTIVE, COMPLETED, CANCELLED)
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.get_user_enrollments(
        x_user_id, page=page, page_size=page_size, status_filter=status_filter
    )


@router.get("/stats", response_model=EnrollmentStatsResponse)
async def get_enrollment_stats(
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enrollment statistics for current user.

    Returns:
    - Total enrollments
    - Active/Completed/Cancelled/Pending counts
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.get_enrollment_stats(x_user_id)


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: int,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enrollment by ID.

    - **enrollment_id**: Enrollment ID
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.get_enrollment_by_id(
        enrollment_id, x_user_id
    )


@router.put("/{enrollment_id}", response_model=EnrollmentResponse)
async def update_enrollment(
    enrollment_id: int,
    enrollment_data: EnrollmentUpdate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Update enrollment (progress, status).

    - **enrollment_id**: Enrollment ID to update
    - **progress_percentage**: Progress (0-100)
    - **status**: New status
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.update_enrollment(
        enrollment_id, enrollment_data, x_user_id
    )


@router.delete("/{enrollment_id}", response_model=MessageResponse)
async def cancel_enrollment(
    enrollment_id: int,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel enrollment.

    - **enrollment_id**: Enrollment ID to cancel
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    await enrollment_service.cancel_enrollment(enrollment_id, x_user_id)
    return MessageResponse(
        message=f"Enrollment {enrollment_id} cancelled successfully"
    )


@router.get(
    "/courses/{course_id}/enrollments",
    response_model=PaginatedEnrollmentResponse,
)
async def get_course_enrollments(
    course_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status_filter: Optional[EnrollmentStatus] = Query(None),
    x_user_id: int = Header(
        ..., description="Instructor ID from auth service"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get enrollments for a course (instructor only).

    - **course_id**: Course ID
    - **page**: Page number
    - **page_size**: Items per page
    - **status**: Filter by status
    """
    enrollment_repository = EnrollmentRepository(db)
    enrollment_service = EnrollmentService(enrollment_repository)
    return await enrollment_service.get_course_enrollments(
        course_id,
        x_user_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )
