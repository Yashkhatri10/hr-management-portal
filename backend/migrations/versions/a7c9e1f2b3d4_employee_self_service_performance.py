"""employee self-service performance progress fields and account mapping

Revision ID: a7c9e1f2b3d4
Revises: f1a2b3c4d5e6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a7c9e1f2b3d4"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    user_columns = {column["name"] for column in inspect(bind).get_columns("users")}
    if "employee_id" not in user_columns:
        op.add_column("users", sa.Column("employee_id", sa.Integer(), nullable=True))
    if "uq_users_employee_id" not in {item["name"] for item in inspect(bind).get_indexes("users")}:
        op.create_index("uq_users_employee_id", "users", ["employee_id"], unique=True)
    if op.get_bind().dialect.name != "sqlite":
        op.create_foreign_key("fk_users_employee_id", "users", "employees", ["employee_id"], ["id"], ondelete="SET NULL")
    op.execute(
        "UPDATE users SET employee_id = "
        "(SELECT employees.id FROM employees WHERE lower(employees.email) = lower(users.email)) "
        "WHERE employee_id IS NULL"
    )
    task_columns = {column["name"] for column in inspect(bind).get_columns("employee_tasks")}
    kra_columns = {column["name"] for column in inspect(bind).get_columns("performance_kras")}
    if "progress_percentage" not in task_columns:
        op.add_column("employee_tasks", sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0"))
    if "progress_notes" not in task_columns:
        op.add_column("employee_tasks", sa.Column("progress_notes", sa.Text(), nullable=True))
    if "progress_percentage" not in kra_columns:
        op.add_column("performance_kras", sa.Column("progress_percentage", sa.Float(), nullable=False, server_default="0"))
    if "progress_notes" not in kra_columns:
        op.add_column("performance_kras", sa.Column("progress_notes", sa.Text(), nullable=True))
    op.execute("UPDATE employee_tasks SET status = 'Not Started' WHERE status = 'Not started'")
    op.execute("UPDATE employee_tasks SET status = 'In Progress' WHERE status = 'In progress'")
    op.execute("UPDATE employee_tasks SET status = 'Pending' WHERE status = 'Blocked'")


def downgrade() -> None:
    op.drop_column("performance_kras", "progress_notes")
    op.drop_column("performance_kras", "progress_percentage")
    op.drop_column("employee_tasks", "progress_notes")
    op.drop_column("employee_tasks", "progress_percentage")
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_users_employee_id", "users", type_="foreignkey")
    op.drop_index("uq_users_employee_id", table_name="users")
    op.drop_column("users", "employee_id")
