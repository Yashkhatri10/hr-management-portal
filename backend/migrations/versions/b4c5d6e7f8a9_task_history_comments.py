"""append-only task history and comments

Revision ID: b4c5d6e7f8a9
Revises: a7c9e1f2b3d4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a7c9e1f2b3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    history_created = not inspect(bind).has_table("employee_task_history")
    if history_created:
        op.create_table(
        "employee_task_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("employee_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_email", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("progress_percentage", sa.Float(), nullable=False),
        sa.Column("progress_notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("employee_task_history")}
    if "ix_employee_task_history_task_id" not in indexes:
        op.create_index("ix_employee_task_history_task_id", "employee_task_history", ["task_id"])
    if "ix_employee_task_history_recorded_at" not in indexes:
        op.create_index("ix_employee_task_history_recorded_at", "employee_task_history", ["recorded_at"])
    if history_created:
        op.execute(
        "INSERT INTO employee_task_history "
        "(task_id, actor_email, status, progress_percentage, progress_notes, recorded_at) "
        "SELECT id, assigned_by, status, progress_percentage, progress_notes, created_at "
        "FROM employee_tasks"
        )
    comments_created = not inspect(bind).has_table("employee_task_comments")
    if comments_created:
        op.create_table(
        "employee_task_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("employee_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_email", sa.String(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        )
    indexes = {item["name"] for item in inspect(bind).get_indexes("employee_task_comments")}
    if "ix_employee_task_comments_task_id" not in indexes:
        op.create_index("ix_employee_task_comments_task_id", "employee_task_comments", ["task_id"])
    if "ix_employee_task_comments_created_at" not in indexes:
        op.create_index("ix_employee_task_comments_created_at", "employee_task_comments", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_employee_task_comments_created_at", table_name="employee_task_comments")
    op.drop_index("ix_employee_task_comments_task_id", table_name="employee_task_comments")
    op.drop_table("employee_task_comments")
    op.drop_index("ix_employee_task_history_recorded_at", table_name="employee_task_history")
    op.drop_index("ix_employee_task_history_task_id", table_name="employee_task_history")
    op.drop_table("employee_task_history")
