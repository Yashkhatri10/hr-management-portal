"""employee lifecycle cases and exit clearance

Revision ID: 85ed1202c1a4
Revises: 6b9b137f249b
Create Date: 2026-10-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "85ed1202c1a4"
down_revision: Union[str, None] = "6b9b137f249b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_lifecycle_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("case_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_lifecycle_cases_id", "employee_lifecycle_cases", ["id"], unique=False)
    op.create_index("ix_employee_lifecycle_cases_employee_id", "employee_lifecycle_cases", ["employee_id"], unique=False)

    op.create_table(
        "exit_clearance_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("owner", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("completed_by", sa.String(length=255), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["employee_lifecycle_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_exit_clearance_items_id", "exit_clearance_items", ["id"], unique=False)
    op.create_index("ix_exit_clearance_items_case_id", "exit_clearance_items", ["case_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_exit_clearance_items_case_id", table_name="exit_clearance_items")
    op.drop_index("ix_exit_clearance_items_id", table_name="exit_clearance_items")
    op.drop_table("exit_clearance_items")
    op.drop_index("ix_employee_lifecycle_cases_employee_id", table_name="employee_lifecycle_cases")
    op.drop_index("ix_employee_lifecycle_cases_id", table_name="employee_lifecycle_cases")
    op.drop_table("employee_lifecycle_cases")