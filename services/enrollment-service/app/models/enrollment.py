"""Enrollment models for Enrollment Service."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

try:
    from app.db.base import Base, TimestampMixin
except ImportError:
    # Fallback for when running migrations
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


class EnrollmentStatus(str, enum.Enum):
    """Enrollment status enumeration."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Enrollment(Base, TimestampMixin):
    """Enrollment model for student course enrollments."""

    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(
            EnrollmentStatus,
            name="enrollmentstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=EnrollmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # 0-100
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<Enrollment(id={self.id}, user_id={self.user_id}, "
            f"course_id={self.course_id}, status={self.status})>"
        )
