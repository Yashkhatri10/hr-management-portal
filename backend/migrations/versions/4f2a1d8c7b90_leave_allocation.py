"""paid and unpaid leave allocation audit fields

Revision ID: 4f2a1d8c7b90
Revises: c3a6c765912e
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4f2a1d8c7b90"
down_revision: Union[str, None] = "c3a6c765912e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("leave_requests")}
    if "paid_days" not in columns:
        op.add_column("leave_requests", sa.Column("paid_days", sa.Numeric(8, 2), nullable=True))
    if "unpaid_days" not in columns:
        op.add_column("leave_requests", sa.Column("unpaid_days", sa.Numeric(8, 2), nullable=True))


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("leave_requests")}
    if "unpaid_days" in columns:
        op.drop_column("leave_requests", "unpaid_days")
    if "paid_days" in columns:
        op.drop_column("leave_requests", "paid_days")
