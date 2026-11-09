from app.database import SessionLocal
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.user import User


def seed_data():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add(
                User(
                    name="Alex Morgan",
                    email="alex.morgan@northstar.io",
                    password="password123",
                    role="HR Manager",
                )
            )

        if db.query(Employee).count() == 0:
            employees = [
                Employee(
                    name="Alex Morgan",
                    email="alex.morgan@northstar.io",
                    role="HR Manager",
                    department="People Operations",
                    location="New York, US",
                    status="Active",
                    manager="Sarah Chen",
                ),
                Employee(
                    name="Priya Shah",
                    email="priya.shah@northstar.io",
                    role="Frontend Engineer",
                    department="Engineering",
                    location="Austin, US",
                    status="Active",
                    manager="Daniel Brooks",
                ),
                Employee(
                    name="Lucas Green",
                    email="lucas.green@northstar.io",
                    role="Recruiter",
                    department="Talent",
                    location="London, UK",
                    status="On Leave",
                    manager="Alex Morgan",
                ),
                Employee(
                    name="Sofia Nguyen",
                    email="sofia.nguyen@northstar.io",
                    role="Finance Analyst",
                    department="Finance",
                    location="Singapore",
                    status="Pending",
                    manager="Rebecca Ross",
                ),
            ]
            db.add_all(employees)

        if db.query(AttendanceRecord).count() == 0:
            attendance = [
                AttendanceRecord(
                    employee_name="Alex Morgan",
                    employee_email="alex.morgan@northstar.io",
                    date="2026-09-27",
                    check_in="09:00",
                    check_out="17:20",
                    status="Present",
                    notes="On time",
                ),
                AttendanceRecord(
                    employee_name="Priya Shah",
                    employee_email="priya.shah@northstar.io",
                    date="2026-09-27",
                    check_in="09:32",
                    check_out="17:40",
                    status="Late",
                    notes="Traffic delay",
                ),
                AttendanceRecord(
                    employee_name="Lucas Green",
                    employee_email="lucas.green@northstar.io",
                    date="2026-09-27",
                    check_in=None,
                    check_out=None,
                    status="Absent",
                    notes="Approved leave",
                ),
            ]
            db.add_all(attendance)

        db.commit()
    finally:
        db.close()
