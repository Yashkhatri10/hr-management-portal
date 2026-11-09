import calendar
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.lifecycle_case import LifecycleCase
from app.models.leave_request import LeaveRequest
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry
from app.models.paid_leave_policy import PaidLeavePolicy

CENT = Decimal("0.01")
DEFAULT_PAID_TYPES = ["Annual", "Paid Leave"]


def today_local() -> date:
    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def quantize_days(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def get_policy(db: Session, on_date: date | None = None) -> PaidLeavePolicy:
    policies = db.query(PaidLeavePolicy).order_by(PaidLeavePolicy.effective_from).all()
    if policies:
        if on_date is None:
            return policies[-1]
        when = on_date
        eligible = [policy for policy in policies if policy.effective_from <= when]
        return eligible[-1] if eligible else policies[0]
    policy = PaidLeavePolicy(
        effective_from=date(2000, 1, 1),
        probation_days=180,
        probation_monthly_days=Decimal("1.00"),
        regular_monthly_days=Decimal("2.50"),
        paid_leave_types_json=json.dumps(DEFAULT_PAID_TYPES),
        allow_negative_balance=False,
        updated_by="system-default",
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def policies_by_date(db: Session) -> list[PaidLeavePolicy]:
    get_policy(db)
    return db.query(PaidLeavePolicy).order_by(PaidLeavePolicy.effective_from).all()


def policy_for_day(policies: list[PaidLeavePolicy], day: date) -> PaidLeavePolicy:
    eligible = [policy for policy in policies if policy.effective_from <= day]
    return eligible[-1] if eligible else policies[0]


def allowed_paid_types(db: Session, on_date: date | None = None) -> set[str]:
    effective_policy = policy_for_day(policies_by_date(db), on_date or today_local())
    return {value.casefold() for value in json.loads(effective_policy.paid_leave_types_json)}


def is_paid_leave_type(db: Session, leave_type: str, on_date: date | None = None) -> bool:
    return leave_type.casefold() in allowed_paid_types(db, on_date)


def business_leave_days(request: LeaveRequest) -> Decimal:
    start = date.fromisoformat(request.start_date)
    end = date.fromisoformat(request.end_date)
    if request.is_half_day:
        if start.weekday() >= 5 or _is_india_national_holiday(start):
            return Decimal("0.00")
        return Decimal("0.50")
    weekdays = sum(
        1
        for offset in range((end - start).days + 1)
        if (start + timedelta(days=offset)).weekday() < 5
        and not _is_india_national_holiday(start + timedelta(days=offset))
    )
    return Decimal(weekdays).quantize(CENT)


def _is_india_national_holiday(day: date) -> bool:
    return (day.month, day.day) in {(1, 26), (8, 15), (10, 2)}


def probation_end_date(db: Session, employee_id: int, start_date: date) -> date:
    policies = policies_by_date(db)
    start_policy = policy_for_day(policies, start_date)
    end_date = start_date + timedelta(days=start_policy.probation_days)
    cases = db.query(LifecycleCase).filter(
        LifecycleCase.employee_id == employee_id,
        LifecycleCase.case_type == "Probation",
    ).order_by(LifecycleCase.created_at).all()
    extensions = 0
    for case in cases:
        try:
            details = json.loads(case.changes_json or "{}")
        except json.JSONDecodeError:
            continue
        if details.get("decision") == "Confirmed":
            return min(end_date + timedelta(days=extensions), case.effective_date)
        if details.get("decision") == "Extended":
            extensions += int(details.get("extension_days") or 0)
    return end_date + timedelta(days=extensions)


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _add_month(day: date) -> date:
    year = day.year + (day.month == 12)
    month = 1 if day.month == 12 else day.month + 1
    return date(year, month, 1)


def _month_key(day: date) -> str:
    return day.strftime("%Y-%m")


def _accrued_days_in_month(
    db: Session,
    employee: Employee,
    profile: EmployeeProfile,
    policies: list[PaidLeavePolicy],
    month: date,
    as_of: date,
) -> Decimal:
    month_end = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
    stop = min(month_end, as_of)
    if not employee.is_active:
        stop = min(stop, profile.employment_end_date or as_of)
    first_day = max(month, profile.start_date)
    if stop < first_day:
        return Decimal("0.00")

    probation_end = probation_end_date(db, employee.id, profile.start_date)
    total = Decimal("0")
    month_days = Decimal(calendar.monthrange(month.year, month.month)[1])
    for offset in range((stop - first_day).days + 1):
        current = first_day + timedelta(days=offset)
        policy = policy_for_day(policies, current)
        if current < probation_end:
            daily = Decimal(policy.probation_monthly_days) / month_days
        else:
            daily = Decimal(policy.regular_monthly_days) / month_days
        total += daily
    return quantize_days(total)


def ensure_monthly_credits(db: Session, as_of: date | None = None) -> None:
    as_of = min(as_of or today_local(), today_local())
    policies = policies_by_date(db)
    employees = db.query(Employee).with_for_update().all()
    profiles = {
        profile.employee_id: profile
        for profile in db.query(EmployeeProfile).filter(EmployeeProfile.employee_id.in_([e.id for e in employees])).all()
    } if employees else {}

    for employee in employees:
        profile = profiles.get(employee.id)
        if profile is None:
            continue
        month = _month_start(profile.start_date)
        last_month = _month_start(as_of)
        while month <= last_month:
            expected = _accrued_days_in_month(db, employee, profile, policies, month, as_of)
            if expected > 0:
                key = _month_key(month)
                source_prefix = f"accrual:{employee.id}:{key}:"
                existing = db.query(func.coalesce(func.sum(PaidLeaveLedgerEntry.amount), 0)).filter(
                    PaidLeaveLedgerEntry.employee_id == employee.id,
                    PaidLeaveLedgerEntry.entry_type == "CREDIT",
                    PaidLeaveLedgerEntry.period_key == key,
                    PaidLeaveLedgerEntry.source_key.like(f"{source_prefix}%"),
                ).scalar()
                existing_total = quantize_days(Decimal(existing or 0))
                delta = quantize_days(expected - existing_total)
                if delta != 0:
                    reconciliation_count = db.query(PaidLeaveLedgerEntry.id).filter(
                        PaidLeaveLedgerEntry.employee_id == employee.id,
                        PaidLeaveLedgerEntry.entry_type == "CREDIT",
                        PaidLeaveLedgerEntry.period_key == key,
                        PaidLeaveLedgerEntry.source_key.like(f"{source_prefix}%"),
                    ).count()
                    db.add(PaidLeaveLedgerEntry(
                        employee_id=employee.id,
                        entry_type="CREDIT",
                        amount=delta,
                        effective_date=as_of,
                        period_key=key,
                        source_key=f"{source_prefix}{as_of.isoformat()}:{reconciliation_count + 1}",
                        note=f"Monthly paid leave accrual true-up for {key}",
                        created_by="system-accrual",
                    ))
            month = _add_month(month)
    db.commit()


def ensure_approved_debits(db: Session, as_of: date | None = None) -> None:
    as_of = as_of or today_local()
    requests = db.query(LeaveRequest).filter(LeaveRequest.status == "Approved").all()
    for request in requests:
        start = date.fromisoformat(request.start_date)
        approval_date = request.approved_at.date() if request.approved_at else start
        if approval_date > as_of:
            continue
        if not db.query(PaidLeaveLedgerEntry.id).filter(PaidLeaveLedgerEntry.source_key == f"leave-debit:{request.id}").first() and not db.query(PaidLeaveLedgerEntry.id).filter(PaidLeaveLedgerEntry.source_key == f"leave-unpaid:{request.id}").first():
            record_paid_leave_debit(db, request, "system-reconciliation")
    db.commit()


def _employee_id_for_request(db: Session, request: LeaveRequest) -> int:
    employee = db.query(Employee).filter(Employee.email == request.employee_email).first()
    if employee is None:
        raise HTTPException(status_code=409, detail=f"No employee record for approved leave request {request.id}")
    return employee.id


def ensure_ledger_current(db: Session, as_of: date | None = None) -> None:
    as_of = min(as_of or today_local(), today_local())
    ensure_monthly_credits(db, as_of)
    ensure_approved_debits(db, as_of)


def ledger_balance(db: Session, employee_id: int, as_of: date | None = None) -> Decimal:
    query = db.query(func.coalesce(func.sum(PaidLeaveLedgerEntry.amount), 0)).filter(PaidLeaveLedgerEntry.employee_id == employee_id)
    if as_of:
        query = query.filter(PaidLeaveLedgerEntry.effective_date <= as_of)
    return quantize_days(Decimal(query.scalar() or 0))


def reject_if_insufficient(db: Session, employee_id: int, requested_days: Decimal) -> None:
    db.query(Employee).filter(Employee.id == employee_id).with_for_update().first()
    ensure_ledger_current(db)
    policy = get_policy(db, today_local())
    balance = ledger_balance(db, employee_id)
    if not policy.allow_negative_balance and balance < requested_days:
        raise HTTPException(status_code=409, detail=f"Insufficient paid leave balance: {balance} days remain; {requested_days} requested")


def record_paid_leave_debit(db: Session, request: LeaveRequest, actor_email: str) -> None:
    start_date = date.fromisoformat(request.start_date)
    exists = db.query(PaidLeaveLedgerEntry.id).filter(
        PaidLeaveLedgerEntry.source_key.in_((f"leave-debit:{request.id}", f"leave-unpaid:{request.id}"))
    ).first()
    if exists:
        return
    days = business_leave_days(request)
    if days <= 0:
        request.paid_days = Decimal("0.00")
        request.unpaid_days = Decimal("0.00")
        return
    employee_id = _employee_id_for_request(db, request)
    paid_days = Decimal("0.00")
    if is_paid_leave_type(db, request.leave_type, start_date):
        ensure_monthly_credits(db)
        paid_days = min(ledger_balance(db, employee_id), days)
    unpaid_days = quantize_days(days - paid_days)
    request.paid_days = quantize_days(paid_days)
    request.unpaid_days = unpaid_days
    effective_date = request.approved_at.date() if request.approved_at else today_local()
    period_key = _month_key(start_date)
    if paid_days > 0:
        db.add(PaidLeaveLedgerEntry(
            employee_id=employee_id, leave_request_id=request.id, entry_type="DEBIT",
            amount=-paid_days, effective_date=effective_date, period_key=period_key,
            source_key=f"leave-debit:{request.id}",
            note=f"Paid allocation for approved leave request #{request.id}", created_by=actor_email,
        ))
    if unpaid_days > 0:
        db.add(PaidLeaveLedgerEntry(
            employee_id=employee_id, leave_request_id=request.id, entry_type="UNPAID",
            amount=unpaid_days, effective_date=effective_date, period_key=period_key,
            source_key=f"leave-unpaid:{request.id}",
            note=f"Unpaid allocation for approved leave request #{request.id}", created_by=actor_email,
        ))


def reverse_paid_leave_debit(db: Session, request: LeaveRequest, actor_email: str) -> None:
    debit = db.query(PaidLeaveLedgerEntry).filter(
        PaidLeaveLedgerEntry.source_key == f"leave-debit:{request.id}"
    ).first()
    if debit is not None:
        source_key = f"leave-reversal:{request.id}"
        if not db.query(PaidLeaveLedgerEntry.id).filter(PaidLeaveLedgerEntry.source_key == source_key).first():
            db.add(PaidLeaveLedgerEntry(
                employee_id=debit.employee_id, leave_request_id=request.id, entry_type="REVERSAL",
                amount=-Decimal(debit.amount), effective_date=today_local(),
                period_key=debit.period_key or _month_key(today_local()),
                source_key=source_key, note=f"Reversal of cancelled paid leave request #{request.id}",
                created_by=actor_email,
            ))
    unpaid = db.query(PaidLeaveLedgerEntry).filter(PaidLeaveLedgerEntry.source_key == f"leave-unpaid:{request.id}").first()
    if unpaid is not None:
        unpaid_reversal_key = f"leave-unpaid-reversal:{request.id}"
        if not db.query(PaidLeaveLedgerEntry.id).filter(PaidLeaveLedgerEntry.source_key == unpaid_reversal_key).first():
            db.add(PaidLeaveLedgerEntry(
                employee_id=unpaid.employee_id, leave_request_id=request.id, entry_type="UNPAID_REVERSAL",
                amount=-Decimal(unpaid.amount), effective_date=today_local(),
                period_key=unpaid.period_key or _month_key(today_local()),
                source_key=unpaid_reversal_key,
                note=f"Reversal of unpaid allocation for cancelled leave request #{request.id}",
                created_by=actor_email,
            ))


def add_adjustment(db: Session, employee_id: int, amount: Decimal, effective_date: date, reason: str, actor_email: str) -> PaidLeaveLedgerEntry:
    ensure_ledger_current(db)
    if effective_date > today_local():
        raise HTTPException(status_code=422, detail="Balance adjustments cannot be future-dated")
    if amount < 0 and not get_policy(db, today_local()).allow_negative_balance and ledger_balance(db, employee_id) < abs(amount):
        raise HTTPException(status_code=409, detail="Adjustment would create a negative leave balance under current policy")
    entry = PaidLeaveLedgerEntry(
        employee_id=employee_id,
        entry_type="ADJUSTMENT",
        amount=quantize_days(amount),
        effective_date=effective_date,
        period_key=_month_key(effective_date),
        source_key=f"adjustment:{employee_id}:{datetime.now(timezone.utc).isoformat()}:{actor_email}",
        note=reason.strip(),
        created_by=actor_email,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def summarize_employee(db: Session, employee: Employee, period_end: date, period_start: date | None = None) -> dict[str, Any]:
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee.id).first()
    entries_query = db.query(PaidLeaveLedgerEntry).filter(
        PaidLeaveLedgerEntry.employee_id == employee.id,
        PaidLeaveLedgerEntry.effective_date <= period_end,
    )
    entries = entries_query.order_by(PaidLeaveLedgerEntry.effective_date, PaidLeaveLedgerEntry.id).all()
    if period_start:
        period_credits = sum((Decimal(item.amount) for item in entries if item.entry_type in {"CREDIT", "ADJUSTMENT"} and item.period_key and _month_start(period_start) <= date.fromisoformat(f"{item.period_key}-01") <= _month_start(period_end)), Decimal(0))
        period_usage = sum((-Decimal(item.amount) for item in entries if item.entry_type == "DEBIT" and item.period_key and _month_start(period_start) <= date.fromisoformat(f"{item.period_key}-01") <= _month_start(period_end)), Decimal(0))
        period_unpaid = sum((Decimal(item.amount) for item in entries if item.entry_type in {"UNPAID", "UNPAID_REVERSAL"} and item.period_key and _month_start(period_start) <= date.fromisoformat(f"{item.period_key}-01") <= _month_start(period_end)), Decimal(0))
    else:
        period_credits = sum((Decimal(item.amount) for item in entries if item.entry_type in {"CREDIT", "ADJUSTMENT"}), Decimal(0))
        period_usage = sum((-Decimal(item.amount) for item in entries if item.entry_type == "DEBIT"), Decimal(0))
        period_unpaid = sum((Decimal(item.amount) for item in entries if item.entry_type in {"UNPAID", "UNPAID_REVERSAL"}), Decimal(0))

    credits = sum((Decimal(item.amount) for item in entries if item.entry_type in {"CREDIT", "ADJUSTMENT"}), Decimal(0))
    adjustments = sum((Decimal(item.amount) for item in entries if item.entry_type == "ADJUSTMENT"), Decimal(0))
    used = sum((Decimal(item.amount) for item in entries if item.entry_type in {"DEBIT", "REVERSAL"}), Decimal(0)) * Decimal(-1)
    unpaid_used = sum((Decimal(item.amount) for item in entries if item.entry_type in {"UNPAID", "UNPAID_REVERSAL"}), Decimal(0))
    remaining = credits - used

    policy = policy_for_day(policies_by_date(db), period_end)
    start_date = profile.start_date if profile else None
    is_probation = bool(start_date and period_end < probation_end_date(db, employee.id, start_date))
    monthly = Decimal(policy.probation_monthly_days if is_probation else policy.regular_monthly_days) if start_date else Decimal("0.00")
    pending_query = db.query(LeaveRequest).filter(
        LeaveRequest.employee_email == employee.email,
        LeaveRequest.status == "Pending",
        LeaveRequest.start_date <= period_end.isoformat(),
        LeaveRequest.end_date >= (period_start or date(1900, 1, 1)).isoformat(),
    )
    pending = pending_query.count()
    utilization = (used / credits * Decimal(100)) if credits > 0 else Decimal(0)
    return {
        "employee_id": employee.id,
        "employee_name": employee.name,
        "email": employee.email,
        "department": employee.department,
        "designation": employee.role,
        "date_of_joining": start_date,
        "employment_status": "Probation" if is_probation else "Regular" if start_date else "Unknown - joining date required",
        "employee_status": employee.status,
        "monthly_entitlement": quantize_days(monthly),
        "total_credited": quantize_days(credits),
        "total_taken": quantize_days(used),
        "total_unpaid": quantize_days(unpaid_used),
        "remaining_balance": quantize_days(remaining),
        "pending_requests": pending,
        "utilization_percent": quantize_days(utilization),
        "period_credited": quantize_days(period_credits),
        "period_taken": quantize_days(period_usage),
        "period_unpaid": quantize_days(period_unpaid),
        "current_month_credit": quantize_days(sum(
            (Decimal(item.amount) for item in entries if item.entry_type == "CREDIT" and item.period_key == _month_key(period_end)),
            Decimal("0"),
        )),
        "opening_balance": quantize_days(sum(
            (Decimal(item.amount) for item in entries if item.period_key and item.period_key < _month_key(period_end)),
            Decimal("0"),
        )),
        "manual_adjustments": quantize_days(adjustments),
        "exhausted": remaining <= 0 and credits > 0,
        "overdrawn": remaining < 0,
        "never_taken": used == 0,
    }
