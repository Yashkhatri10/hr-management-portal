from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.employee import Employee
from app.models.onboarding_task import OnboardingTask
from app.models.leave_request import LeaveRequest
from app.models.attendance import AttendanceRecord
from app.config import settings
from app.services.paid_leave import ensure_ledger_current, summarize_employee

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    is_hr_manager = user.role == "HR Manager"
    employee_count = db.query(Employee).filter(Employee.is_active.is_(True)).count() if is_hr_manager else 1
    personal_leave_requests = db.query(LeaveRequest).filter(LeaveRequest.employee_email == user.email).all()
    leave_requests = db.query(LeaveRequest).all() if is_hr_manager else personal_leave_requests
    today = datetime.now(ZoneInfo(settings.app_timezone)).date()
    ensure_ledger_current(db)
    signed_in_employee = db.query(Employee).filter(Employee.email == user.email).first()
    personal_paid_leave = summarize_employee(db, signed_in_employee, today) if signed_in_employee else None
    used_leave_days = personal_paid_leave["total_taken"] if personal_paid_leave else 0
    leave_balance = personal_paid_leave["remaining_balance"] if personal_paid_leave else 0
    upcoming_leave_count = sum(
        1
        for req in leave_requests
        if req.status in {"Approved", "Pending"}
        and req.start_date
        and date.fromisoformat(req.start_date) >= today
    )

    upcoming_leave_schedule = [
        f"{req.employee_name} — {req.start_date} to {req.end_date} ({req.leave_type})"
        for req in sorted(
            leave_requests,
            key=lambda req: date.fromisoformat(req.start_date) if req.start_date else date.max,
        )
        if req.status in {"Approved", "Pending"}
        and (is_hr_manager or req.employee_email == user.email)
    ]

    if is_hr_manager:
        pending_leave_count = db.query(LeaveRequest).filter(LeaveRequest.status == "Pending").count()
        pending_onboarding_count = db.query(OnboardingTask).filter(OnboardingTask.status != "Completed").count()
        pending_tasks = pending_leave_count + pending_onboarding_count
        attendance_query = db.query(AttendanceRecord).filter(
            AttendanceRecord.date == today.isoformat(),
            AttendanceRecord.status.in_(["Present", "Late"]),
        )
        attended_today = attendance_query.count()
        active_employees = max(employee_count, 1)
        attendance_rate = round((attended_today / active_employees) * 100)
    else:
        pending_tasks = sum(1 for req in personal_leave_requests if req.status == "Pending")
        today_attendance = db.query(AttendanceRecord).filter(
            AttendanceRecord.employee_email == user.email,
            AttendanceRecord.date == today.isoformat(),
        ).first()
        attendance_rate = 100 if today_attendance and today_attendance.status in {"Present", "Late"} else 0

    return {
        "summary": {
            "totalEmployees": employee_count,
            "openPositions": 0,
            "attendance": attendance_rate,
            "pendingTasks": pending_tasks,
            "leaveBalance": leave_balance,
            "upcomingLeaves": upcoming_leave_count,
            "usedLeaves": used_leave_days,
        },
        "recentActivity": [],
        "upcomingHires": [],
        "upcomingLeaveSchedule": upcoming_leave_schedule,
    }
