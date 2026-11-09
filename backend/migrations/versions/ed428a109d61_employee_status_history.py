"""employee lifecycle status history

Revision ID: ed428a109d61
Revises: c3a6c765912e
Create Date: 2026-10-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "ed428a109d61"
down_revision: Union[str, None] = "c3a6c765912e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("employee_status_events"):
        op.create_table(
            "employee_status_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("employee_id", sa.Integer(), nullable=False),
            sa.Column("previous_status", sa.String(length=30), nullable=False),
            sa.Column("new_status", sa.String(length=30), nullable=False),
            sa.Column("effective_date", sa.Date(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("changed_by", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    indexes = {index["name"] for index in inspect(bind).get_indexes("employee_status_events")}
    if "ix_employee_status_events_id" not in indexes:
        op.create_index("ix_employee_status_events_id", "employee_status_events", ["id"], unique=False)
    if "ix_employee_status_events_employee_id" not in indexes:
        op.create_index("ix_employee_status_events_employee_id", "employee_status_events", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_employee_status_events_employee_id", table_name="employee_status_events")
    op.drop_index("ix_employee_status_events_id", table_name="employee_status_events")
    op.drop_table("employee_status_events")
