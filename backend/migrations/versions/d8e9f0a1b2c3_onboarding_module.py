"""onboarding records, templates, documents and notifications

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "d8e9f0a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = {
        "onboarding_records": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="In Progress"),
            sa.Column("onboarding_start_date", sa.Date()), sa.Column("deadline", sa.Date()),
            sa.Column("coordinator_email", sa.String()), sa.Column("notes", sa.Text()),
            sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("completed_by", sa.String()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        ],
        "onboarding_templates": [
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(160), nullable=False, unique=True),
            sa.Column("description", sa.Text()), sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        ],
        "onboarding_template_items": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("template_id", sa.Integer(), sa.ForeignKey("onboarding_templates.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(160), nullable=False), sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("owner", sa.String(40), nullable=False, server_default="HR"), sa.Column("mandatory", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("due_days", sa.Integer()), sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        ],
        "onboarding_documents": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(160), nullable=False), sa.Column("document_type", sa.String(80), nullable=False),
            sa.Column("filename", sa.String(255), nullable=False), sa.Column("storage_name", sa.String(255), nullable=False, unique=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="Uploaded"), sa.Column("rejection_reason", sa.Text()),
            sa.Column("uploaded_by", sa.String(), nullable=False), sa.Column("verified_by", sa.String()),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("verified_at", sa.DateTime()),
        ],
        "onboarding_notifications": [
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE")),
            sa.Column("recipient_email", sa.String(), nullable=False), sa.Column("message", sa.String(500), nullable=False),
            sa.Column("link", sa.String(255)), sa.Column("event_key", sa.String(180), nullable=False, unique=True),
            sa.Column("read_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        ],
    }
    for name, columns in tables.items():
        if not inspect(bind).has_table(name):
            op.create_table(name, *columns)
    if inspect(bind).has_table("onboarding_tasks"):
        columns = {item["name"] for item in inspect(bind).get_columns("onboarding_tasks")}
        for name, definition in (("mandatory", sa.Column("mandatory", sa.Boolean(), nullable=False, server_default="1")), ("comments", sa.Column("comments", sa.Text())), ("updated_by", sa.Column("updated_by", sa.String(255))), ("updated_at", sa.Column("updated_at", sa.DateTime()))):
            if name not in columns:
                op.add_column("onboarding_tasks", definition)


def downgrade() -> None:
    for name in ("onboarding_notifications", "onboarding_documents", "onboarding_template_items", "onboarding_templates", "onboarding_records"):
        op.drop_table(name)
