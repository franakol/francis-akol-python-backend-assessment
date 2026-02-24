"""Course repository for database operations."""

from typing import List, Optional

from app.models.course import Category, Course, CourseContent
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class CourseRepository:
    """Repository for Course database operations."""

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session."""
        self.db = db

    # Course operations
    async def create_course(
        self, course_data: dict, instructor_id: int
    ) -> Course:
        """Create a new course."""
        course = Course(**course_data, instructor_id=instructor_id)
        self.db.add(course)
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def get_course_by_id(
        self, course_id: int, include_contents: bool = True
    ) -> Optional[Course]:
        """Get course by ID with optional content loading."""
        query = select(Course).where(Course.id == course_id)

        if include_contents:
            query = query.options(
                selectinload(Course.category), selectinload(Course.contents)
            )
        else:
            query = query.options(selectinload(Course.category))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_courses(
        self,
        skip: int = 0,
        limit: int = 100,
        category_id: Optional[int] = None,
        instructor_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> List[Course]:
        """Get list of courses with filtering and pagination."""
        query = select(Course).options(selectinload(Course.category))

        # Apply filters
        if category_id is not None:
            query = query.where(Course.category_id == category_id)

        if instructor_id is not None:
            query = query.where(Course.instructor_id == instructor_id)

        if is_published is not None:
            query = query.where(Course.is_published == is_published)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Course.title.ilike(search_term),
                    Course.description.ilike(search_term),
                )
            )

        # Apply sorting
        if sort_by == "title":
            order_column = Course.title
        elif sort_by == "price":
            order_column = Course.price
        elif sort_by == "enrolled_count":
            order_column = Course.enrolled_count
        else:  # default to created_at
            order_column = Course.created_at

        if sort_order == "asc":
            query = query.order_by(order_column.asc())
        else:
            query = query.order_by(order_column.desc())

        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count_courses(
        self,
        category_id: Optional[int] = None,
        instructor_id: Optional[int] = None,
        is_published: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> int:
        """Count total courses with optional filters."""
        query = select(func.count()).select_from(Course)

        if category_id is not None:
            query = query.where(Course.category_id == category_id)

        if instructor_id is not None:
            query = query.where(Course.instructor_id == instructor_id)

        if is_published is not None:
            query = query.where(Course.is_published == is_published)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Course.title.ilike(search_term),
                    Course.description.ilike(search_term),
                )
            )

        result = await self.db.execute(query)
        return result.scalar_one()

    async def update_course(self, course: Course) -> Course:
        """Update course."""
        await self.db.commit()
        await self.db.refresh(course)
        return course

    async def delete_course(self, course: Course) -> None:
        """Delete course."""
        await self.db.delete(course)
        await self.db.commit()

    async def increment_enrolled_count(self, course_id: int) -> None:
        """Increment enrolled count for a course."""
        course = await self.get_course_by_id(course_id, include_contents=False)
        if course:
            course.enrolled_count += 1
            await self.db.commit()

    # Course Content operations
    async def create_course_content(
        self, course_id: int, content_data: dict
    ) -> CourseContent:
        """Create course content."""
        content = CourseContent(**content_data, course_id=course_id)
        self.db.add(content)
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def get_course_contents(self, course_id: int) -> List[CourseContent]:
        """Get all contents for a course."""
        result = await self.db.execute(
            select(CourseContent)
            .where(CourseContent.course_id == course_id)
            .order_by(CourseContent.order)
        )
        return list(result.scalars().all())

    async def get_course_content_by_id(
        self, content_id: int
    ) -> Optional[CourseContent]:
        """Get course content by ID."""
        result = await self.db.execute(
            select(CourseContent).where(CourseContent.id == content_id)
        )
        return result.scalar_one_or_none()

    async def update_course_content(
        self, content: CourseContent
    ) -> CourseContent:
        """Update course content."""
        await self.db.commit()
        await self.db.refresh(content)
        return content

    async def delete_course_content(self, content: CourseContent) -> None:
        """Delete course content."""
        await self.db.delete(content)
        await self.db.commit()

    # Category operations
    async def create_category(self, category_data: dict) -> Category:
        """Create a category."""
        category = Category(**category_data)
        self.db.add(category)
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        """Get category by ID."""
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_category_by_slug(self, slug: str) -> Optional[Category]:
        """Get category by slug."""
        result = await self.db.execute(
            select(Category).where(Category.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_categories(self) -> List[Category]:
        """Get all categories."""
        result = await self.db.execute(
            select(Category).order_by(Category.name)
        )
        return list(result.scalars().all())

    async def update_category(self, category: Category) -> Category:
        """Update category."""
        await self.db.commit()
        await self.db.refresh(category)
        return category

    async def delete_category(self, category: Category) -> None:
        """Delete category."""
        await self.db.delete(category)
        await self.db.commit()
