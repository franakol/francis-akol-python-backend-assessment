"""Pytest configuration and fixtures for Course Service tests."""

import asyncio
from typing import AsyncGenerator, Generator


import pytest
from app.core.config import settings
from app.db.base import Base
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "/course_service_db", "/course_service_test_db"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def mock_instructor_token() -> str:
    """Return a mock JWT token for an instructor."""
    return "mock-instructor-jwt-token"


@pytest.fixture
def mock_admin_token() -> str:
    """Return a mock JWT token for an admin."""
    return "mock-admin-jwt-token"


@pytest.fixture
def mock_student_token() -> str:
    """Return a mock JWT token for a student."""
    return "mock-student-jwt-token"


@pytest.fixture
def sample_course_data() -> dict:
    """Return sample course data for testing."""
    return {
        "title": "Python Mastery",
        "description": "Complete Python programming course from beginner to advanced",
        "price": "99.99",
        "max_students": 100,
        "category_id": None,
        "thumbnail_url": "https://example.com/python-course.jpg",
    }


@pytest.fixture
def sample_category_data() -> dict:
    """Return sample category data for testing."""
    return {
        "name": "Programming",
        "description": "Software development and programming courses",
    }


@pytest.fixture
def sample_content_data() -> dict:
    """Return sample course content data for testing."""
    return {
        "title": "Introduction to Python",
        "content_type": "video",
        "content_url": "https://example.com/videos/intro.mp4",
        "duration_minutes": 30,
        "order": 1,
        "is_preview": True,
    }
