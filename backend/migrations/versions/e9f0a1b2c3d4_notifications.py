"""add authenticated user notifications

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "e9f0a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("notification_type", sa.String(60), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("module", sa.String(40), nullable=False),
            sa.Column("related_record_id", sa.Integer()),
            sa.Column("action_link", sa.String(255)),
            sa.Column("event_key", sa.String(255), nullable=False, unique=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("read_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    inspector = inspect(bind)
    if inspector.has_table("notifications"):
        existing_indexes = {index["name"] for index in inspector.get_indexes("notifications")}
        for name, columns in {
            "recipient_user_id": ["recipient_user_id", "ix_notifications_recipient_user"],
            "module": ["module", "ix_notifications_module"],
            "is_read": ["is_read", "ix_notifications_is_read"],
            "created_at": ["created_at", "ix_notifications_created_at"],
        }.items():
            if name in {column["name"] for column in inspector.get_columns("notifications")} and columns[1] not in existing_indexes:
                op.create_index(columns[1], "notifications", [name], unique=False)


def downgrade() -> None:
    if inspect(op.get_bind()).has_table("notifications"):
        op.drop_table("notifications")
