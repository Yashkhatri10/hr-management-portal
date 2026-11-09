"""employee 360 activities, tasks and performance management

Revision ID: f1a2b3c4d5e6
Revises: ed428a109d61
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = ("ed428a109d61", "8d3f5a7b1c20")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_table(name: str, *columns) -> None:
    if not inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns)


def upgrade() -> None:
    _create_table(
        "employee_activities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_email", sa.String(), nullable=False),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("activity_date", sa.Date(), nullable=False),
        sa.Column("metadata_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "employee_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("assigned_by", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("due_date", sa.Date()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "performance_kras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "performance_kpis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kra_id", sa.Integer(), sa.ForeignKey("performance_kras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("actual_value", sa.Float()),
        sa.Column("unit", sa.String(length=40)),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "performance_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_email", sa.String(), nullable=False),
        sa.Column("review_period", sa.String(length=40), nullable=False),
        sa.Column("review_type", sa.String(length=40), nullable=False),
        sa.Column("overall_score", sa.Float()),
        sa.Column("strengths", sa.Text()),
        sa.Column("development_areas", sa.Text()),
        sa.Column("comments", sa.Text()),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "performance_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("review_id", sa.Integer(), sa.ForeignKey("performance_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_email", sa.String(), nullable=False),
        sa.Column("relationship", sa.String(length=40), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("comments", sa.Text()),
        sa.Column("anonymous", sa.Boolean(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
    )
    _create_table(
        "performance_kpi_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kpi_id", sa.Integer(), sa.ForeignKey("performance_kpis.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actual_value", sa.Float(), nullable=False),
        sa.Column("achievement_percentage", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("recorded_by", sa.String(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(), nullable=False),
    )
    if "ix_performance_kpi_history_kpi_id" not in {item["name"] for item in inspect(op.get_bind()).get_indexes("performance_kpi_history")}:
        op.create_index("ix_performance_kpi_history_kpi_id", "performance_kpi_history", ["kpi_id"])
    _create_table(
        "employee_progress_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("achievements", sa.Text()),
        sa.Column("blockers", sa.Text()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="Draft"),
        sa.Column("review_feedback", sa.Text()),
        sa.Column("reviewer_email", sa.String()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    if "ix_employee_progress_reports_employee_id" not in {item["name"] for item in inspect(op.get_bind()).get_indexes("employee_progress_reports")}:
        op.create_index("ix_employee_progress_reports_employee_id", "employee_progress_reports", ["employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employee_progress_reports_employee_id", table_name="employee_progress_reports")
    op.drop_table("employee_progress_reports")
    op.drop_index("ix_performance_kpi_history_kpi_id", table_name="performance_kpi_history")
    op.drop_table("performance_kpi_history")
    op.drop_table("performance_feedback")
    op.drop_table("performance_reviews")
    op.drop_table("performance_kpis")
    op.drop_table("performance_kras")
    op.drop_table("employee_tasks")
    op.drop_table("employee_activities")
