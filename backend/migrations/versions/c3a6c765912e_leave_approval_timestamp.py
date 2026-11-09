"""leave approval timestamp for paid leave audit

Revision ID: c3a6c765912e
Revises: 9d482bc721af
Create Date: 2026-10-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3a6c765912e"
down_revision: Union[str, None] = "9d482bc721af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("leave_requests", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("leave_requests", "approved_at")