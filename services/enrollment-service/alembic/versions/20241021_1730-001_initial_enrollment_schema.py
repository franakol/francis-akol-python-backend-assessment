"""Initial enrollment schema

Revision ID: 001
Revises:
Create Date: 2024-10-21 17:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enrollmentstatus enum (if not exists)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE enrollmentstatus AS ENUM "
        "('pending', 'active', 'completed', 'cancelled'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # Create enrollments table
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "active",
                "completed",
                "cancelled",
                name="enrollmentstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "progress_percentage",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "last_accessed_at", sa.DateTime(timezone=True), nullable=True
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
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    op.create_index(
        op.f("ix_enrollments_id"), "enrollments", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_enrollments_user_id"),
        "enrollments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enrollments_course_id"),
        "enrollments",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_enrollments_status"), "enrollments", ["status"], unique=False
    )

    # Create unique constraint for user_id + course_id (prevent duplicate active enrollments)
    op.create_index(
        "ix_enrollments_user_course_unique",
        "enrollments",
        ["user_id", "course_id"],
        unique=False,
    )

    # Create trigger for auto-update timestamps
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
        CREATE TRIGGER update_enrollments_updated_at BEFORE UPDATE ON enrollments
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    )


def downgrade() -> None:
    # Drop triggers
    op.execute(
        "DROP TRIGGER IF EXISTS update_enrollments_updated_at ON enrollments;"
    )
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop indexes
    op.drop_index(
        "ix_enrollments_user_course_unique", table_name="enrollments"
    )
    op.drop_index(op.f("ix_enrollments_status"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_course_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_user_id"), table_name="enrollments")
    op.drop_index(op.f("ix_enrollments_id"), table_name="enrollments")

    # Drop table
    op.drop_table("enrollments")

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS enrollmentstatus;")
