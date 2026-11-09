"""face templates and geofence state

Revision ID: 8d3f5a7b1c20
Revises: 7c2d4e8f9a10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "8d3f5a7b1c20"
down_revision: Union[str, None] = "7c2d4e8f9a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("face_templates"):
        op.create_table(
            "face_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False, unique=True),
            sa.Column("embedding", sa.Text(), nullable=False),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("enrolled_by", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    indexes = {index["name"] for index in inspect(bind).get_indexes("face_templates")}
    if "ix_face_templates_employee_id" not in indexes:
        op.create_index("ix_face_templates_employee_id", "face_templates", ["employee_id"], unique=True)
    existing = {column["name"] for column in inspect(bind).get_columns("attendance_records")}
    for name, column in (
        ("geofence_exit_confirmations", sa.Column("geofence_exit_confirmations", sa.Integer(), nullable=False, server_default="0")),
        ("geofence_outside_since", sa.Column("geofence_outside_since", sa.DateTime(timezone=True), nullable=True)),
        ("checkout_reason", sa.Column("checkout_reason", sa.String(), nullable=True)),
    ):
        if name not in existing:
            op.add_column("attendance_records", column)


def downgrade() -> None:
    op.drop_column("attendance_records", "checkout_reason")
    op.drop_column("attendance_records", "geofence_outside_since")
    op.drop_column("attendance_records", "geofence_exit_confirmations")
    op.drop_index("ix_face_templates_employee_id", table_name="face_templates")
    op.drop_table("face_templates")
