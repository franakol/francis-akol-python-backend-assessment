"""Course endpoints."""

from typing import Optional

from app.core.dependencies import get_db
from app.repositories.course_repository import CourseRepository
from app.schemas.course import (
    CourseContentCreate,
    CourseContentResponse,
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    MessageResponse,
    PaginatedCourseResponse,
)
from app.services.course_service import CourseService
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED
)
async def create_course(
    course_data: CourseCreate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new course (instructor only).

    - **title**: Course title
    - **description**: Course description
    - **category_id**: Category ID (optional)
    - **price**: Course price
    - **max_students**: Maximum students (optional)
    """
    course_repository = CourseRepository(db)
    course_service = CourseService(course_repository)
    return await course_service.create_course(course_data, x_user_id)


@router.get("/", response_model=PaginatedCourseResponse)
async def get_courses(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    category_id: Optional[int] = Query(None),
    instructor_id: Optional[int] = Query(None),
    is_published: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query(
        "created_at", regex="^(title|price|created_at|enrolled_count)$"
    ),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get paginated list of courses with filtering and sorting.

    - **page**: Page number
    - **page_size**: Items per page
    - **category_id**: Filter by category
    - **instructor_id**: Filter by instructor
    - **is_published**: Filter by published status
    - **search**: Search in title and description
    - **sort_by**: Sort field (title, price, created_at, enrolled_count)
    - **sort_order**: Sort order (asc, desc)
    """
    course_repository = CourseRepository(db)
    course_service = CourseService(course_repository)
    return await course_service.get_courses(
        page=page,
        page_size=page_size,
        category_id=category_id,
        instructor_id=instructor_id,
        is_published=is_published,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get course details by ID (cached).

    - **course_id**: Course ID
    """
    course_repository = CourseRepository(db)
    course_service = CourseService(course_repository)
    return await course_service.get_course_by_id(course_id)


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_data: CourseUpdate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Update course (instructor only).

    - **course_id**: Course ID to update
    """
    course_repository = CourseRepository(db)
    course_service = CourseService(course_repository)
    return await course_service.update_course(
        course_id, course_data, x_user_id
    )


@router.delete("/{course_id}", response_model=MessageResponse)
async def delete_course(
    course_id: int,
    x_user_id: int = Header(..., description="User ID from auth service"),
    x_is_admin: bool = Header(False, description="Is admin user"),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete course (instructor or admin).

    - **course_id**: Course ID to delete
    """
    course_repository = CourseRepository(db)
    course_service = CourseService(course_repository)
    await course_service.delete_course(course_id, x_user_id, x_is_admin)
    return MessageResponse(message=f"Course {course_id} deleted successfully")


@router.post(
    "/{course_id}/content",
    response_model=CourseContentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_course_content(
    course_id: int,
    content_data: CourseContentCreate,
    x_user_id: int = Header(..., description="User ID from auth service"),
    db: AsyncSession = Depends(get_db),
):
    """
    Create course content (instructor only).

    - **course_id**: Course ID
    - **content_data**: Content information
    """
    course_repository = CourseRepository(db)

    # Verify course exists and user is instructor
    course = await course_repository.get_course_by_id(
        course_id, include_contents=False
    )
    if not course:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Course not found")

    if course.instructor_id != x_user_id:
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Not authorized")

    content = await course_repository.create_course_content(
        course_id, content_data.model_dump()
    )

    # Invalidate cache
    from app.core.cache import cache

    await cache.delete(f"course:{course_id}")

    return CourseContentResponse.model_validate(content)


@router.get("/{course_id}/content", response_model=list[CourseContentResponse])
async def get_course_contents(
    course_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all content for a course.

    - **course_id**: Course ID
    """
    course_repository = CourseRepository(db)
    contents = await course_repository.get_course_contents(course_id)
    return [
        CourseContentResponse.model_validate(content) for content in contents
    ]
