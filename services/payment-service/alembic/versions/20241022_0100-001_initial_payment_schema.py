"""Initial payment schema

Revision ID: 001
Revises:
Create Date: 2024-10-22 01:00:00.000000

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
    # Create paymentstatus enum (if not exists)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE paymentstatus AS ENUM "
        "('pending', 'completed', 'failed', 'refunded'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # Create paymentmethod enum (if not exists)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE paymentmethod AS ENUM "
        "('credit_card', 'debit_card', 'paypal', 'stripe', 'bank_transfer'); "
        "EXCEPTION WHEN duplicate_object THEN null; END $$;"
    )

    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
            server_default="USD",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending",
                "completed",
                "failed",
                "refunded",
                name="paymentstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "payment_method",
            postgresql.ENUM(
                "credit_card",
                "debit_card",
                "paypal",
                "stripe",
                "bank_transfer",
                name="paymentmethod",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.String(length=255), nullable=True),
        sa.Column("payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("refund_reason", sa.Text(), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.Text(), nullable=True),
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
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(
        op.f("ix_payments_user_id"), "payments", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_payments_course_id"), "payments", ["course_id"], unique=False
    )
    op.create_index(
        op.f("ix_payments_enrollment_id"),
        "payments",
        ["enrollment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_payments_status"), "payments", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_payments_transaction_id"),
        "payments",
        ["transaction_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_payments_payment_intent_id"),
        "payments",
        ["payment_intent_id"],
        unique=False,
    )

    # Create composite index for user_id + course_id (common query pattern)
    op.create_index(
        "ix_payments_user_course",
        "payments",
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
        CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON payments
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    )


def downgrade() -> None:
    # Drop triggers
    op.execute(
        "DROP TRIGGER IF EXISTS update_payments_updated_at ON payments;"
    )
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")

    # Drop indexes
    op.drop_index("ix_payments_user_course", table_name="payments")
    op.drop_index(op.f("ix_payments_payment_intent_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_transaction_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_status"), table_name="payments")
    op.drop_index(op.f("ix_payments_enrollment_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_course_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_user_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")

    # Drop table
    op.drop_table("payments")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS paymentmethod;")
    op.execute("DROP TYPE IF EXISTS paymentstatus;")
