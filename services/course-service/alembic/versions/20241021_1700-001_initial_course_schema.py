"""Initial course schema

Revision ID: 001
Revises:
Create Date: 2024-10-21 17:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create categories table
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_categories_id"), "categories", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_categories_name"), "categories", ["name"], unique=True
    )
    op.create_index(
        op.f("ix_categories_slug"), "categories", ["slug"], unique=True
    )

    # Create courses table
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column(
            "price",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("max_students", sa.Integer(), nullable=True),
        sa.Column(
            "enrolled_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_id"), "courses", ["id"], unique=False)
    op.create_index(
        op.f("ix_courses_title"), "courses", ["title"], unique=False
    )
    op.create_index(
        op.f("ix_courses_instructor_id"),
        "courses",
        ["instructor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_courses_category_id"),
        "courses",
        ["category_id"],
        unique=False,
    )

    # Create course_contents table
    op.create_table(
        "course_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=False),
        sa.Column("content_url", sa.String(length=500), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_preview", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_course_contents_id"), "course_contents", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_course_contents_course_id"),
        "course_contents",
        ["course_id"],
        unique=False,
    )

    # Create full-text search index on course title and description
    op.execute(
        """
        CREATE INDEX idx_courses_fulltext ON courses
        USING gin(to_tsvector('english', title || ' ' || description))
    """
    )

    # Create triggers for auto-update timestamps
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    )

    op.execute(
        """
        CREATE TRIGGER update_course_contents_updated_at BEFORE UPDATE ON course_contents
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    )


def downgrade() -> None:
    # Drop triggers
    op.execute(
        "DROP TRIGGER IF EXISTS update_course_contents_updated_at ON course_contents;"
    )
    op.execute("DROP TRIGGER IF EXISTS update_courses_updated_at ON courses;")
    op.execute(
        "DROP TRIGGER IF EXISTS update_categories_updated_at ON categories;"
    )
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop tables
    op.drop_index(
        op.f("ix_course_contents_course_id"), table_name="course_contents"
    )
    op.drop_index(op.f("ix_course_contents_id"), table_name="course_contents")
    op.drop_table("course_contents")

    op.execute("DROP INDEX IF EXISTS idx_courses_fulltext;")
    op.drop_index(op.f("ix_courses_category_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_instructor_id"), table_name="courses")
    op.drop_index(op.f("ix_courses_title"), table_name="courses")
    op.drop_index(op.f("ix_courses_id"), table_name="courses")
    op.drop_table("courses")

    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
