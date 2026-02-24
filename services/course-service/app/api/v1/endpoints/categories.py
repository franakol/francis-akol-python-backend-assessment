"""Category endpoints."""

from app.core.dependencies import get_db
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CategoryCreate, CategoryResponse
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post(
    "/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new category (admin only in production).

    - **name**: Category name
    - **description**: Category description
    """
    course_repository = CourseRepository(db)

    # Generate slug from name
    slug = category_data.name.lower().replace(" ", "-")

    # Check if slug already exists
    existing = await course_repository.get_category_by_slug(slug)
    if existing:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400, detail="Category with this name already exists"
        )

    category = await course_repository.create_category(
        {**category_data.model_dump(), "slug": slug}
    )
    return CategoryResponse.model_validate(category)


@router.get("/", response_model=list[CategoryResponse])
async def get_categories(
    db: AsyncSession = Depends(get_db),
):
    """Get all categories."""
    course_repository = CourseRepository(db)
    categories = await course_repository.get_categories()
    return [CategoryResponse.model_validate(cat) for cat in categories]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get category by ID."""
    course_repository = CourseRepository(db)
    category = await course_repository.get_category_by_id(category_id)

    if not category:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Category not found")

    return CategoryResponse.model_validate(category)
