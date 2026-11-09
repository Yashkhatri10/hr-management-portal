"""employee 360 goals, development plans and document metadata

Revision ID: c7d8e9f0a1b2
Revises: b4c5d6e7f8a9
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table, columns in (
        ("employee_goals", [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
            sa.Column("status", sa.String(30), nullable=False, server_default="Not Started"),
            sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("target_date", sa.Date()), sa.Column("created_by", sa.String(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        ]),
        ("development_plans", [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
            sa.Column("actions", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="Draft"),
            sa.Column("target_date", sa.Date()), sa.Column("created_by", sa.String(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        ]),
        ("employee_documents", [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
            sa.Column("document_type", sa.String(60), nullable=False), sa.Column("title", sa.String(200), nullable=False),
            sa.Column("issuer", sa.String(200)), sa.Column("reference_number", sa.String(120)),
            sa.Column("issued_date", sa.Date()), sa.Column("expiry_date", sa.Date()),
            sa.Column("status", sa.String(30), nullable=False, server_default="Active"), sa.Column("notes", sa.Text()),
            sa.Column("created_by", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        ]),
    ):
        if not inspect(bind).has_table(table):
            op.create_table(table, *columns)
        if f"ix_{table}_employee_id" not in {item["name"] for item in inspect(bind).get_indexes(table)}:
            op.create_index(f"ix_{table}_employee_id", table, ["employee_id"])


def downgrade() -> None:
    for table in ("employee_documents", "development_plans", "employee_goals"):
        op.drop_index(f"ix_{table}_employee_id", table_name=table)
        op.drop_table(table)
