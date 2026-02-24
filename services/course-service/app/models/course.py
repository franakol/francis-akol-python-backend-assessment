"""Course models for Course Service."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

try:
    from app.db.base import Base, TimestampMixin
except ImportError:
    # Fallback for when running migrations
    from sqlalchemy import DateTime
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

    class TimestampMixin:
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )


class Category(Base, TimestampMixin):
    """Category model for course categorization."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )

    # Relationships
    courses: Mapped[List["Course"]] = relationship(
        "Course", back_populates="category"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name})>"


class Course(Base, TimestampMixin):
    """Course model."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    instructor_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0.00
    )
    max_students: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    enrolled_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )

    # Relationships
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="courses"
    )
    contents: Mapped[List["CourseContent"]] = relationship(
        "CourseContent",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="CourseContent.order",
    )

    def __repr__(self) -> str:
        return f"<Course(id={self.id}, title={self.title}, instructor_id={self.instructor_id})>"


class CourseContent(Base, TimestampMixin):
    """Course content model."""

    __tablename__ = "course_contents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # video, document, quiz, etc.
    content_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_preview: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Free preview content

    # Relationships
    course: Mapped["Course"] = relationship(
        "Course", back_populates="contents"
    )

    def __repr__(self) -> str:
        return f"<CourseContent(id={self.id}, course_id={self.course_id}, title={self.title})>"
