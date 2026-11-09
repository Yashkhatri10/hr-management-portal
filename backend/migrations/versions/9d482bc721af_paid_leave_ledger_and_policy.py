"""paid leave ledger, policy versions and cancellation fields

Revision ID: 9d482bc721af
Revises: 85ed1202c1a4
Create Date: 2026-10-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9d482bc721af"
down_revision: Union[str, None] = "85ed1202c1a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employee_profiles", sa.Column("employment_end_date", sa.Date(), nullable=True))
    op.add_column("leave_requests", sa.Column("is_half_day", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("leave_requests", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "paid_leave_policies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("probation_days", sa.Integer(), nullable=False),
        sa.Column("probation_monthly_days", sa.Numeric(6, 2), nullable=False),
        sa.Column("regular_monthly_days", sa.Numeric(6, 2), nullable=False),
        sa.Column("paid_leave_types_json", sa.Text(), nullable=False),
        sa.Column("allow_negative_balance", sa.Boolean(), nullable=False),
        sa.Column("updated_by", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("effective_from"),
    )
    op.create_index("ix_paid_leave_policies_effective_from", "paid_leave_policies", ["effective_from"], unique=True)

    op.create_table(
        "paid_leave_ledger",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("leave_request_id", sa.Integer(), nullable=True),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("amount", sa.Numeric(8, 2), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("period_key", sa.String(length=7), nullable=True),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leave_request_id"], ["leave_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_key", name="uq_paid_leave_ledger_source_key"),
    )
    op.create_index("ix_paid_leave_ledger_id", "paid_leave_ledger", ["id"], unique=False)
    op.create_index("ix_paid_leave_ledger_employee_id", "paid_leave_ledger", ["employee_id"], unique=False)
    op.create_index("ix_paid_leave_ledger_leave_request_id", "paid_leave_ledger", ["leave_request_id"], unique=False)
    op.create_index("ix_paid_leave_ledger_effective_date", "paid_leave_ledger", ["effective_date"], unique=False)
    op.create_index("ix_paid_leave_ledger_period_key", "paid_leave_ledger", ["period_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_paid_leave_ledger_period_key", table_name="paid_leave_ledger")
    op.drop_index("ix_paid_leave_ledger_effective_date", table_name="paid_leave_ledger")
    op.drop_index("ix_paid_leave_ledger_leave_request_id", table_name="paid_leave_ledger")
    op.drop_index("ix_paid_leave_ledger_employee_id", table_name="paid_leave_ledger")
    op.drop_index("ix_paid_leave_ledger_id", table_name="paid_leave_ledger")
    op.drop_table("paid_leave_ledger")
    op.drop_index("ix_paid_leave_policies_effective_from", table_name="paid_leave_policies")
    op.drop_table("paid_leave_policies")
    op.drop_column("leave_requests", "cancelled_at")
    op.drop_column("leave_requests", "is_half_day")
    op.drop_column("employee_profiles", "employment_end_date")
