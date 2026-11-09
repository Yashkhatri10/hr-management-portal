import json
from calendar import monthrange
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_hr_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.leave_request import LeaveRequest
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry
from app.models.paid_leave_policy import PaidLeavePolicy
from app.models.user import User
from app.schemas.paid_leave import PaidLeaveAdjustment, PaidLeavePolicyUpdate
from app.services.paid_leave import (
    add_adjustment,
    business_leave_days,
    ensure_ledger_current,
    get_policy,
    ledger_balance,
    probation_end_date,
    summarize_employee,
    today_local,
)

router = APIRouter(prefix="/paid-leave", tags=["paid leave"])


def resolve_period(period_type: str, period: str | None) -> tuple[date, date, str]:
    today = today_local()
    try:
        if period_type == "month":
            if period:
                year, month = (int(part) for part in period.split("-", 1))
            else:
                year, month = today.year, today.month
            if not 1 <= month <= 12:
                raise ValueError("month")
            return date(year, month, 1), date(year, month, monthrange(year, month)[1]), f"{year:04d}-{month:02d}"
        if period_type == "quarter":
            if period:
                year_text, quarter_text = period.split("-Q", 1)
                year, quarter = int(year_text), int(quarter_text)
            else:
                year, quarter = today.year, (today.month - 1) // 3 + 1
            if not 1 <= quarter <= 4:
                raise ValueError("quarter")
            first_month = 1 + (quarter - 1) * 3
            last_month = first_month + 2
            return date(year, first_month, 1), date(year, last_month, monthrange(year, last_month)[1]), f"{year}-Q{quarter}"
        if period_type == "financial_year":
            if period:
                start_year = int(period.split("-", 1)[0])
            else:
                start_year = today.year if today.month >= 4 else today.year - 1
            return date(start_year, 4, 1), date(start_year + 1, 3, 31), f"{start_year}-{str(start_year + 1)[-2:]}"
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid period format") from exc
    raise HTTPException(status_code=422, detail="period_type must be month, quarter, or financial_year")


@router.get("/policy")
def read_policy(db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    policy = get_policy(db)
    return {
        "id": policy.id,
        "effective_from": policy.effective_from,
        "probation_days": policy.probation_days,
        "probation_monthly_days": Decimal(policy.probation_monthly_days),
        "regular_monthly_days": Decimal(policy.regular_monthly_days),
        "paid_leave_types": json.loads(policy.paid_leave_types_json),
        "allow_negative_balance": policy.allow_negative_balance,
    }


@router.put("/policy")
def update_policy(payload: PaidLeavePolicyUpdate, db: Session = Depends(get_db), actor: User = Depends(require_hr_manager)):
    get_policy(db)
    latest = db.query(PaidLeavePolicy).order_by(PaidLeavePolicy.effective_from.desc()).first()
    today = today_local()
    effective_date = date(today.year + (today.month == 12), 1 if today.month == 12 else today.month + 1, 1)
    if latest and latest.effective_from > effective_date:
        effective_date = latest.effective_from
    policy = db.query(PaidLeavePolicy).filter(PaidLeavePolicy.effective_from == effective_date).first()
    if policy is None:
        policy = PaidLeavePolicy(effective_from=effective_date, updated_by=actor.email)
        db.add(policy)
    policy.probation_days = payload.probation_days
    policy.probation_monthly_days = payload.probation_monthly_days
    policy.regular_monthly_days = payload.regular_monthly_days
    policy.paid_leave_types_json = json.dumps(payload.paid_leave_types)
    policy.allow_negative_balance = payload.allow_negative_balance
    policy.updated_by = actor.email
    db.commit()
    return read_policy(db, _hr=actor)


@router.get("/report")
def paid_leave_report(
    period_type: str = Query(default="month"),
    period: str | None = None,
    search: str = "",
    department: str = "",
    designation: str = "",
    probation_status: str = "",
    employment_status: str = "",
    sort_by: str = "employee_name",
    db: Session = Depends(get_db),
    _hr=Depends(require_hr_manager),
):
    start, end, label = resolve_period(period_type, period)
    as_of = min(end, today_local())
    ensure_ledger_current(db, as_of)
    employees = db.query(Employee).order_by(Employee.name).all()
    rows = [summarize_employee(db, employee, as_of, start) for employee in employees]
    query = search.casefold().strip()
    if query:
        rows = [row for row in rows if query in row["employee_name"].casefold() or query in str(row["employee_id"]) or query in row["email"].casefold()]
    if department:
        rows = [row for row in rows if row["department"].casefold() == department.casefold()]
    if designation:
        rows = [row for row in rows if row["designation"].casefold() == designation.casefold()]
    if probation_status:
        rows = [row for row in rows if row["employment_status"].casefold() == probation_status.casefold()]
    if employment_status:
        rows = [row for row in rows if row["employee_status"].casefold() == employment_status.casefold()]

    sort_map = {
        "employee_name": lambda row: row["employee_name"].casefold(),
        "remaining_balance": lambda row: row["remaining_balance"],
        "utilization": lambda row: row["utilization_percent"],
        "leave_taken": lambda row: row["total_taken"],
    }
    if sort_by not in sort_map:
        raise HTTPException(status_code=422, detail="Unsupported sort_by")
    rows.sort(key=sort_map[sort_by], reverse=sort_by != "employee_name")
    return {"period_type": period_type, "period": label, "period_start": start, "period_end": end, "as_of": as_of, "employees": rows}


@router.get("/employees/{employee_id}")
def employee_paid_leave_details(
    employee_id: int,
    period_type: str = Query(default="financial_year"),
    period: str | None = None,
    db: Session = Depends(get_db),
    _hr=Depends(require_hr_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    start, end, label = resolve_period(period_type, period)
    as_of = min(end, today_local())
    ensure_ledger_current(db, as_of)
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    probation_end = probation_end_date(db, employee_id, profile.start_date) if profile else None
    entries = db.query(PaidLeaveLedgerEntry).filter(
        PaidLeaveLedgerEntry.employee_id == employee_id,
        PaidLeaveLedgerEntry.effective_date <= as_of,
    ).order_by(PaidLeaveLedgerEntry.effective_date, PaidLeaveLedgerEntry.id).all()
    requests = db.query(LeaveRequest).filter(LeaveRequest.employee_email == employee.email).order_by(LeaveRequest.start_date.desc()).all()

    first_month = max(date(start.year, start.month, 1), date(profile.start_date.year, profile.start_date.month, 1) if profile else date(start.year, start.month, 1))
    last_month = date(as_of.year, as_of.month, 1)
    future_periods = [date.fromisoformat(f"{entry.period_key}-01") for entry in entries if entry.period_key]
    if future_periods:
        last_month = max(last_month, max(future_periods))
    month_keys: list[str] = []
    cursor = first_month
    while cursor <= last_month:
        month_keys.append(cursor.strftime("%Y-%m"))
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    monthly_history = []
    period_start_month = date(first_month.year, first_month.month, 1)
    running_balance = sum((Decimal(entry.amount) for entry in entries if entry.period_key and date.fromisoformat(f"{entry.period_key}-01") < period_start_month), Decimal("0.00"))
    entries_by_period: dict[str, list[PaidLeaveLedgerEntry]] = {}
    for entry in entries:
        key = entry.period_key or entry.effective_date.strftime("%Y-%m")
        entries_by_period.setdefault(key, []).append(entry)
    requests_by_period: dict[str, list[LeaveRequest]] = {}
    for request in requests:
        requests_by_period.setdefault(request.start_date[:7], []).append(request)
    for key in month_keys:
        opening = running_balance
        month_entries = entries_by_period.get(key, [])
        credited = sum((Decimal(item.amount) for item in month_entries if item.entry_type == "CREDIT"), Decimal(0))
        used = -sum((Decimal(item.amount) for item in month_entries if item.entry_type == "DEBIT"), Decimal(0))
        unpaid_used = sum((Decimal(item.amount) for item in month_entries if item.entry_type in {"UNPAID", "UNPAID_REVERSAL"}), Decimal(0))
        reversed_days = sum((Decimal(item.amount) for item in month_entries if item.entry_type == "REVERSAL"), Decimal(0))
        month_adjustments = sum((Decimal(item.amount) for item in month_entries if item.entry_type == "ADJUSTMENT"), Decimal(0))
        net = sum((Decimal(item.amount) for item in month_entries), Decimal(0))
        running_balance += net
        monthly_history.append({"month": key, "opening_balance": opening, "credited": credited, "carried_forward": opening, "used": used, "unpaid_used": unpaid_used, "reversed": reversed_days, "adjustments": month_adjustments, "closing_balance": running_balance})

    return {
        "employee": {
            "id": employee.id,
            "name": employee.name,
            "email": employee.email,
            "department": employee.department,
            "designation": employee.role,
            "employment_status": employee.status,
            "date_of_joining": profile.start_date if profile else None,
            "probation_end_date": probation_end,
            "regular_start_date": probation_end,
        },
        "period": label,
        "balance": summarize_employee(db, employee, as_of, start),
        "ledger": [
            {
                "id": entry.id,
                "type": entry.entry_type,
                "amount": Decimal(entry.amount),
                "effective_date": entry.effective_date,
                "period": entry.period_key,
                "note": entry.note,
                "created_by": entry.created_by,
                "created_at": entry.created_at,
            }
            for entry in entries
        ],
        "requests": [
            {
                "id": req.id,
                "type": req.leave_type,
                "start_date": req.start_date,
                "end_date": req.end_date,
                "days": business_leave_days(req),
                "paid_days": Decimal(req.paid_days or 0),
                "unpaid_days": Decimal(req.unpaid_days or 0),
                "is_half_day": req.is_half_day,
                "status": req.status,
                "reason": req.reason,
            }
            for req in requests
        ],
        "monthly_history": monthly_history,
    }


@router.get("/me")
def my_paid_leave_balance(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = db.query(Employee).filter(Employee.email == user.email).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    today = today_local()
    ensure_ledger_current(db)
    return summarize_employee(db, employee, today)


@router.post("/employees/{employee_id}/adjustments")
def create_adjustment(
    employee_id: int,
    payload: PaidLeaveAdjustment,
    db: Session = Depends(get_db),
    actor: User = Depends(require_hr_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    entry = add_adjustment(db, employee_id, payload.amount, payload.effective_date, payload.reason, actor.email)
    return {"id": entry.id, "employee_id": entry.employee_id, "amount": Decimal(entry.amount), "effective_date": entry.effective_date}
