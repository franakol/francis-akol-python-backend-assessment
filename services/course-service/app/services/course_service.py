"""Course service with Redis caching."""

import math
from typing import Optional

from app.core.cache import cache
from app.repositories.course_repository import CourseRepository
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CourseResponse,
    CourseUpdate,
    PaginatedCourseResponse,
)
from fastapi import HTTPException, status


class CourseService:
    """Service for course operations with caching."""

    def __init__(self, course_repository: CourseRepository):
        """Initialize course service with repository."""
        self.course_repository = course_repository

    async def create_course(
        self, course_data: CourseCreate, instructor_id: int
    ) -> CourseResponse:
        """Create a new course."""
        # Create course in database
        course = await self.course_repository.create_course(
            course_data.model_dump(), instructor_id
        )

        # Invalidate cache for course list
        await cache.delete_pattern("courses:list:*")

        # Get course with relationships
        course = await self.course_repository.get_course_by_id(course.id)
        return CourseResponse.model_validate(course)

    async def get_course_by_id(
        self, course_id: int, use_cache: bool = True
    ) -> CourseResponse:
        """
        Get course by ID with caching.

        Args:
            course_id: Course ID
            use_cache: Whether to use cache (default: True)

        Returns:
            Course response

        Raises:
            HTTPException: If course not found
        """
        cache_key = f"course:{course_id}"

        # Try to get from cache
        if use_cache:
            cached_course = await cache.get(cache_key)
            if cached_course:
                return CourseResponse(**cached_course)

        # Get from database
        course = await self.course_repository.get_course_by_id(course_id)

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        course_response = CourseResponse.model_validate(course)

        # Cache the result
        if use_cache:
            await cache.set(cache_key, course_response.model_dump(mode="json"))

        return course_response

    async def get_courses(
        self,
        page: int = 1,
        page_size: int = 10,
        category_id: Optional[int] = None,
        instructor_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        use_cache: bool = True,
    ) -> PaginatedCourseResponse:
        """Get paginated list of courses with caching."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        skip = (page - 1) * page_size

        # Generate cache key based on parameters
        cache_key = (
            f"courses:list:page={page}:size={page_size}:cat={category_id}:"
            f"inst={instructor_id}:pub={is_published}:search={search}:"
            f"sort={sort_by}:{sort_order}"
        )

        # Try to get from cache
        if use_cache:
            cached_result = await cache.get(cache_key)
            if cached_result:
                return PaginatedCourseResponse(**cached_result)

        # Get courses and total count
        courses = await self.course_repository.get_courses(
            skip=skip,
            limit=page_size,
            category_id=category_id,
            instructor_id=instructor_id,
            is_published=is_published,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total = await self.course_repository.count_courses(
            category_id=category_id,
            instructor_id=instructor_id,
            is_published=is_published,
            search=search,
        )

        # Calculate total pages
        total_pages = math.ceil(total / page_size)

        result = PaginatedCourseResponse(
            items=[
                CourseListResponse.model_validate(course) for course in courses
            ],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        # Cache the result
        if use_cache:
            await cache.set(cache_key, result.model_dump(mode="json"))

        return result

    async def update_course(
        self, course_id: int, course_data: CourseUpdate, instructor_id: int
    ) -> CourseResponse:
        """Update a course."""
        course = await self.course_repository.get_course_by_id(
            course_id, include_contents=False
        )

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Check if user is the instructor
        if course.instructor_id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this course",
            )

        # Update fields
        update_dict = course_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(course, key, value)

        course = await self.course_repository.update_course(course)

        # Invalidate cache
        await cache.delete(f"course:{course_id}")
        await cache.delete_pattern("courses:list:*")

        # Get updated course with relationships
        course = await self.course_repository.get_course_by_id(course_id)
        return CourseResponse.model_validate(course)

    async def delete_course(
        self, course_id: int, instructor_id: int, is_admin: bool = False
    ) -> None:
        """Delete a course."""
        course = await self.course_repository.get_course_by_id(
            course_id, include_contents=False
        )

        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )

        # Check authorization (instructor or admin)
        if not is_admin and course.instructor_id != instructor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this course",
            )

        await self.course_repository.delete_course(course)

        # Invalidate cache
        await cache.delete(f"course:{course_id}")
        await cache.delete_pattern("courses:list:*")
