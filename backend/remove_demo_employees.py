"""Back up the local SQLite database and remove only the known starter employees.

Run from backend after stopping the API and setting SEED_DEMO_DATA=false in .env.
The HR Manager login is retained; no leave-request history is removed.
"""
from datetime import datetime
from pathlib import Path
import sqlite3

from sqlalchemy import delete, select

from app.config import settings
from app.database import SessionLocal, engine
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.onboarding_task import OnboardingTask
from app.models.user import User

DEMO_EMAILS = (
    "alex.morgan@northstar.io",
    "priya.shah@northstar.io",
    "lucas.green@northstar.io",
    "sofia.nguyen@northstar.io",
)


def make_sqlite_backup() -> Path:
    if engine.dialect.name != "sqlite":
        raise SystemExit("This cleanup script is for the local SQLite demo database only.")
    database_path = Path(engine.url.database or "hr_portal.db").resolve()
    if not database_path.exists():
        raise SystemExit(f"Database not found: {database_path}")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(f"{database_path.stem}-before-demo-cleanup-{timestamp}{database_path.suffix}")
    source = sqlite3.connect(str(database_path))
    destination = sqlite3.connect(str(backup_path))
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    return backup_path


def main() -> None:
    if settings.app_env.lower() == "production":
        raise SystemExit("Refusing to run against APP_ENV=production.")
    if settings.seed_demo_data:
        raise SystemExit("Set SEED_DEMO_DATA=false in backend/.env and restart/stop the API before cleanup.")

    db = SessionLocal()
    try:
        employees = db.scalars(select(Employee).where(Employee.email.in_(DEMO_EMAILS))).all()
        if not employees:
            raise SystemExit("No known starter demo employees found; nothing changed.")

        print("Starter employee records to remove:")
        for employee in employees:
            print(f"  - {employee.name} <{employee.email}>")
        print("The Alex Morgan HR Manager login will be retained.")
        print("No leave-request history will be deleted.")
        confirmation = input('Type REMOVE DEMO EMPLOYEES to continue: ').strip()
        if confirmation != "REMOVE DEMO EMPLOYEES":
            raise SystemExit("Cancelled; no records changed.")

        backup_path = make_sqlite_backup()
        employee_ids = [employee.id for employee in employees]
        demo_attendance_dates = ["2026-09-27"]
        db.execute(delete(OnboardingTask).where(OnboardingTask.employee_id.in_(employee_ids)))
        db.execute(delete(EmployeeProfile).where(EmployeeProfile.employee_id.in_(employee_ids)))
        db.execute(
            delete(AttendanceRecord).where(
                AttendanceRecord.employee_email.in_(DEMO_EMAILS),
                AttendanceRecord.date.in_(demo_attendance_dates),
                AttendanceRecord.notes.in_(["On time", "Traffic delay", "Approved leave"]),
            )
        )
        db.execute(delete(Employee).where(Employee.id.in_(employee_ids)))
        # Keep the seeded HR Manager account so you can still log in and add real staff.
        db.execute(
            delete(User).where(
                User.email.in_(DEMO_EMAILS),
                User.email != "alex.morgan@northstar.io",
            )
        )
        db.commit()
        print(f"Removed {len(employees)} starter employee records.")
        print(f"Database backup saved at: {backup_path}")
        print("The HR Manager login remains available. Register real employees from the Employees page.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
