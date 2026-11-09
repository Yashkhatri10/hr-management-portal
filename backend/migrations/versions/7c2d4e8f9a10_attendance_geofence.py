"""attendance GPS fields

Revision ID: 7c2d4e8f9a10
Revises: 4f2a1d8c7b90
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "7c2d4e8f9a10"
down_revision: Union[str, None] = "4f2a1d8c7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {column["name"] for column in inspect(op.get_bind()).get_columns("attendance_records")}
    for name in (
        "check_in_latitude", "check_in_longitude", "check_in_accuracy_meters",
        "check_in_distance_meters", "check_out_latitude", "check_out_longitude",
        "check_out_accuracy_meters", "check_out_distance_meters",
    ):
        if name not in existing:
            op.add_column("attendance_records", sa.Column(name, sa.Float(), nullable=True))


def downgrade() -> None:
    for name in (
        "check_out_distance_meters", "check_out_accuracy_meters", "check_out_longitude",
        "check_out_latitude", "check_in_distance_meters", "check_in_accuracy_meters",
        "check_in_longitude", "check_in_latitude",
    ):
        op.drop_column("attendance_records", name)
