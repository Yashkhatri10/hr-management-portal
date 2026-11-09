from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

DATABASE_URL = settings.database_url
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite:") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_runtime_schema() -> None:
    if not DATABASE_URL.startswith("sqlite:"):
        return
    # SQLite deployments may start from a database created before a migration
    # was introduced.  Creating only the additive tables is safe and idempotent.
    additive_tables = (
        "performance_kpi_history", "employee_progress_reports",
        "employee_task_history", "employee_task_comments", "employee_goals",
        "development_plans", "employee_documents",
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[name] for name in additive_tables if name in Base.metadata.tables],
        checkfirst=True,
    )
    inspector = inspect(engine)
    onboarding_tables = (
        "onboarding_records", "onboarding_templates", "onboarding_template_items",
        "onboarding_documents", "onboarding_notifications",
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[Base.metadata.tables[name] for name in onboarding_tables if name in Base.metadata.tables],
        checkfirst=True,
    )
    if "notifications" in Base.metadata.tables:
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["notifications"]], checkfirst=True)
    task_columns = {column["name"] for column in inspector.get_columns("onboarding_tasks")} if inspector.has_table("onboarding_tasks") else set()
    with engine.begin() as connection:
        for name, column_type in (
            ("mandatory", "BOOLEAN NOT NULL DEFAULT 1"),
            ("comments", "TEXT"),
            ("updated_by", "VARCHAR(255)"),
            ("updated_at", "DATETIME"),
        ):
            if task_columns and name not in task_columns:
                connection.execute(text(f"ALTER TABLE onboarding_tasks ADD COLUMN {name} {column_type}"))
    if not inspector.has_table("users") or not inspector.has_table("employees"):
        return
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    performance_columns = {
        table: ({column["name"] for column in inspector.get_columns(table)}
                if inspector.has_table(table) else set())
        for table in ("employee_tasks", "performance_kras")
    }
    with engine.begin() as connection:
        if "employee_id" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN employee_id INTEGER"))
        connection.execute(text(
            "UPDATE users SET employee_id = (SELECT employees.id FROM employees "
            "WHERE lower(employees.email) = lower(users.email)) "
            "WHERE employee_id IS NULL"
        ))
        task_types = {
            "progress_percentage": "FLOAT NOT NULL DEFAULT 0",
            "progress_notes": "TEXT",
        }
        for name, column_type in task_types.items():
            if performance_columns["employee_tasks"] and name not in performance_columns["employee_tasks"]:
                connection.execute(text(f"ALTER TABLE employee_tasks ADD COLUMN {name} {column_type}"))
            if performance_columns["performance_kras"] and name not in performance_columns["performance_kras"]:
                connection.execute(text(f"ALTER TABLE performance_kras ADD COLUMN {name} {column_type}"))
        if performance_columns["employee_tasks"]:
            connection.execute(text(
                "UPDATE employee_tasks SET status = 'Not Started' WHERE status = 'Not started'"
            ))
            connection.execute(text(
                "UPDATE employee_tasks SET status = 'In Progress' WHERE status = 'In progress'"
            ))
            connection.execute(text(
                "UPDATE employee_tasks SET status = 'Pending' WHERE status = 'Blocked'"
            ))
            connection.execute(text(
                "INSERT INTO employee_task_history "
                "(task_id, actor_email, status, progress_percentage, progress_notes, recorded_at) "
                "SELECT t.id, t.assigned_by, t.status, t.progress_percentage, t.progress_notes, t.created_at "
                "FROM employee_tasks t "
                "WHERE NOT EXISTS (SELECT 1 FROM employee_task_history h WHERE h.task_id = t.id)"
            ))
    if not inspector.has_table("leave_requests"):
        columns = set()
    else:
        columns = {column["name"] for column in inspector.get_columns("leave_requests")}
    if columns:
        with engine.begin() as connection:
            if "paid_days" not in columns:
                connection.execute(text("ALTER TABLE leave_requests ADD COLUMN paid_days NUMERIC(8, 2)"))
            if "unpaid_days" not in columns:
                connection.execute(text("ALTER TABLE leave_requests ADD COLUMN unpaid_days NUMERIC(8, 2)"))
    if not inspector.has_table("attendance_records"):
        return
    attendance_columns = {column["name"] for column in inspector.get_columns("attendance_records")}
    attendance_types = {
        "check_in_latitude": "FLOAT", "check_in_longitude": "FLOAT", "check_in_accuracy_meters": "FLOAT",
        "check_in_distance_meters": "FLOAT", "check_out_latitude": "FLOAT", "check_out_longitude": "FLOAT",
        "check_out_accuracy_meters": "FLOAT", "check_out_distance_meters": "FLOAT",
        "geofence_exit_confirmations": "INTEGER", "geofence_outside_since": "DATETIME",
        "checkout_reason": "VARCHAR",
    }
    with engine.begin() as connection:
        for name, column_type in attendance_types.items():
            if name not in attendance_columns:
                connection.execute(text(f"ALTER TABLE attendance_records ADD COLUMN {name} {column_type}"))
