import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import require_hr_manager
from app.config import settings
from app.database import get_db
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.employee_status_event import EmployeeStatusEvent
from app.models.exit_clearance import ExitClearanceItem
from app.models.lifecycle_case import LifecycleCase
from app.models.user import User
from app.schemas.lifecycle import ClearanceUpdate, EmployeeLifecycleOut, LifecycleCaseCreate, LifecycleDecision
from app.schemas.employee_status import EmployeeStatusUpdate
from app.services.paid_leave import probation_end_date

router = APIRouter(prefix="/employees", tags=["employee lifecycle"], dependencies=[Depends(require_hr_manager)])
CLEARANCE_TEMPLATE = [
    ("Return company equipment", "IT"),
    ("Revoke system and building access", "IT"),
    ("Handover work and documentation", "Manager"),
    ("Reconcile expenses and advances", "Finance"),
    ("Complete payroll and benefits settlement", "Payroll"),
    ("Conduct exit interview and archive HR records", "HR"),
]


def _today() -> date:
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo(settings.app_timezone)).date()


def _employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.patch("/{employee_id}/status")
def update_employee_status(
    employee_id: int,
    payload: EmployeeStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_hr_manager),
):
    employee = _employee_or_404(db, employee_id)
    if payload.status == employee.status:
        raise HTTPException(status_code=409, detail="Employee already has this status")
    if not employee.is_active and payload.status not in {"Resigned", "Terminated", "Inactive"}:
        raise HTTPException(status_code=409, detail="Archived employee cannot be returned to active status here")
    previous_status = employee.status
    employee.status = payload.status
    employee.is_active = payload.status not in {"Resigned", "Terminated", "Inactive"}
    if not employee.is_active:
        profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee.id).first()
        if profile and profile.employment_end_date is None:
            profile.employment_end_date = payload.effective_date
        account = db.query(User).filter(User.email == employee.email).first()
        if account:
            account.is_active = False
    event = EmployeeStatusEvent(
        employee_id=employee.id,
        previous_status=previous_status,
        new_status=payload.status,
        effective_date=payload.effective_date,
        reason=payload.reason.strip(),
        changed_by=actor.email,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {
        "id": event.id,
        "employee_id": employee.id,
        "previous_status": event.previous_status,
        "new_status": event.new_status,
        "effective_date": event.effective_date,
        "reason": event.reason,
        "changed_by": event.changed_by,
        "created_at": event.created_at,
    }


def _case_out(case: LifecycleCase, db: Session) -> dict:
    return {
        "id": case.id,
        "employee_id": case.employee_id,
        "case_type": case.case_type,
        "status": case.status,
        "effective_date": case.effective_date,
        "reason": case.reason,
        "changes": json.loads(case.changes_json or "{}"),
        "created_by": case.created_by,
        "created_at": case.created_at,
        "decided_at": case.decided_at,
        "clearance": db.query(ExitClearanceItem).filter(ExitClearanceItem.case_id == case.id).order_by(ExitClearanceItem.id).all(),
    }


def _apply_due_approved_cases(employee: Employee, db: Session) -> None:
    cases = db.query(LifecycleCase).filter(
        LifecycleCase.employee_id == employee.id,
        LifecycleCase.status == "Approved",
        LifecycleCase.case_type.in_(["Transfer", "Promotion"]),
        LifecycleCase.effective_date <= _today(),
    ).order_by(LifecycleCase.effective_date, LifecycleCase.id).all()
    for case in cases:
        changes = json.loads(case.changes_json or "{}")
        for field in ("department", "location", "manager", "role"):
            if changes.get(field) is not None:
                setattr(employee, field, changes[field])
        case.status = "Applied"
    if cases:
        db.commit()


@router.get("/{employee_id}/lifecycle", response_model=EmployeeLifecycleOut)
def get_employee_lifecycle(employee_id: int, db: Session = Depends(get_db)):
    employee = _employee_or_404(db, employee_id)
    _apply_due_approved_cases(employee, db)
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    start_date = profile.start_date if profile else None
    probation_due = probation_end_date(db, employee_id, start_date) if start_date else None
    cases = db.query(LifecycleCase).filter(LifecycleCase.employee_id == employee_id).order_by(LifecycleCase.created_at.desc()).all()
    probation_status = "In progress"
    for case in cases:
        if case.case_type == "Probation":
            changes = json.loads(case.changes_json or "{}")
            probation_status = changes.get("decision", "In progress")
            if changes.get("extension_days") and probation_due:
                probation_due += timedelta(days=int(changes["extension_days"]))
            break
    if probation_status == "In progress" and probation_due and probation_due < _today():
        probation_status = "Review overdue"
    return {
        "employee_id": employee.id,
        "employee_name": employee.name,
        "department": employee.department,
        "location": employee.location,
        "role": employee.role,
        "manager": employee.manager,
        "start_date": start_date,
        "probation_due_date": probation_due,
        "probation_status": probation_status,
        "cases": [_case_out(case, db) for case in cases],
        "status_history": db.query(EmployeeStatusEvent).filter(
            EmployeeStatusEvent.employee_id == employee_id
        ).order_by(EmployeeStatusEvent.effective_date.desc(), EmployeeStatusEvent.id.desc()).all(),
    }


@router.post("/{employee_id}/lifecycle", response_model=EmployeeLifecycleOut, status_code=201)
def create_lifecycle_case(
    employee_id: int,
    payload: LifecycleCaseCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_hr_manager),
):
    employee = _employee_or_404(db, employee_id)
    if not employee.is_active:
        raise HTTPException(status_code=409, detail="Cannot create a lifecycle case for an inactive employee")
    existing_pending = db.query(LifecycleCase).filter(
        LifecycleCase.employee_id == employee_id,
        LifecycleCase.status == "Pending",
    ).first()
    if existing_pending:
        raise HTTPException(status_code=409, detail="Resolve the existing pending lifecycle case first")
    if payload.effective_date < _today():
        raise HTTPException(status_code=422, detail="Effective date cannot be in the past")
    if payload.case_type in {"Transfer", "Promotion"} and not any((payload.department, payload.location, payload.manager, payload.role, payload.new_salary)):
        raise HTTPException(status_code=422, detail="Provide at least one proposed change")
    if payload.case_type == "Resignation" and payload.last_working_date and payload.last_working_date < payload.effective_date:
        raise HTTPException(status_code=422, detail="Last working date cannot be before the resignation effective date")

    changes = {
        "department": payload.department,
        "location": payload.location,
        "manager": payload.manager,
        "role": payload.role,
        "new_salary": payload.new_salary,
        "last_working_date": payload.last_working_date.isoformat() if payload.last_working_date else None,
    }
    case = LifecycleCase(
        employee_id=employee_id,
        case_type=payload.case_type,
        status="Pending",
        effective_date=payload.effective_date,
        reason=payload.reason.strip(),
        changes_json=json.dumps(changes),
        created_by=actor.email,
    )
    db.add(case)
    db.flush()
    if payload.case_type == "Resignation":
        db.add_all([ExitClearanceItem(case_id=case.id, title=title, owner=owner) for title, owner in CLEARANCE_TEMPLATE])
    db.commit()
    return get_employee_lifecycle(employee_id, db)


@router.patch("/lifecycle/cases/{case_id}/decision")
def decide_lifecycle_case(
    case_id: int,
    payload: LifecycleDecision,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_hr_manager),
):
    case = db.query(LifecycleCase).filter(LifecycleCase.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Lifecycle case not found")
    if case.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending cases can be approved or rejected")
    case.status = payload.status
    case.decided_at = datetime.now(timezone.utc)
    if case.case_type == "Resignation" and payload.status == "Approved":
        employee = _employee_or_404(db, case.employee_id)
        previous_status = employee.status
        employee.status = "On Notice"
        db.add(EmployeeStatusEvent(
            employee_id=employee.id,
            previous_status=previous_status,
            new_status="On Notice",
            effective_date=case.effective_date,
            reason=f"Resignation approved: {case.reason}",
            changed_by=_actor.email,
        ))
    db.commit()
    return {"id": case.id, "status": case.status, "decided_at": case.decided_at}


@router.patch("/lifecycle/clearance/{item_id}")
def update_exit_clearance(
    item_id: int,
    payload: ClearanceUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_hr_manager),
):
    item = db.query(ExitClearanceItem).filter(ExitClearanceItem.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Exit clearance item not found")
    case = db.query(LifecycleCase).filter(LifecycleCase.id == item.case_id).first()
    if case is None or case.case_type != "Resignation" or case.status != "Approved":
        raise HTTPException(status_code=409, detail="Exit clearance is available only after resignation approval")
    if item.status == "Completed":
        raise HTTPException(status_code=409, detail="Clearance item is already completed")
    item.status = payload.status
    item.completed_by = actor.email if item.status == "Completed" else None
    item.completed_at = datetime.now(timezone.utc) if item.status == "Completed" else None
    db.commit()
    return {"id": item.id, "status": item.status, "completed_by": item.completed_by}


@router.post("/lifecycle/cases/{case_id}/complete-offboarding")
def complete_offboarding(
    case_id: int,
    db: Session = Depends(get_db),
    _actor: User = Depends(require_hr_manager),
):
    case = db.query(LifecycleCase).filter(LifecycleCase.id == case_id, LifecycleCase.case_type == "Resignation").first()
    if case is None:
        raise HTTPException(status_code=404, detail="Resignation case not found")
    if case.status != "Approved":
        raise HTTPException(status_code=409, detail="Approve the resignation before completing offboarding")
    case_changes = json.loads(case.changes_json or "{}")
    last_working_date = case_changes.get("last_working_date")
    if last_working_date and date.fromisoformat(last_working_date) > _today():
        raise HTTPException(status_code=409, detail="Offboarding cannot close before the last working date")
    items = db.query(ExitClearanceItem).filter(ExitClearanceItem.case_id == case_id).all()
    incomplete = [item.title for item in items if item.status != "Completed"]
    if incomplete:
        raise HTTPException(status_code=409, detail=f"Complete all exit clearance tasks first ({len(incomplete)} remaining)")

    employee = _employee_or_404(db, case.employee_id)
    previous_status = employee.status
    employee.status = "Resigned"
    employee.is_active = False
    db.add(EmployeeStatusEvent(
        employee_id=employee.id,
        previous_status=previous_status,
        new_status="Resigned",
        effective_date=date.fromisoformat(last_working_date) if last_working_date else _today(),
        reason=f"Offboarding completed for resignation case #{case.id}",
        changed_by=_actor.email,
    ))
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee.id).first()
    if profile:
        try:
            profile.employment_end_date = date.fromisoformat(last_working_date) if last_working_date else _today()
        except (ValueError, KeyError):
            profile.employment_end_date = _today()
    account = db.query(User).filter(User.email == employee.email).first()
    if account:
        account.is_active = False
    case.status = "Closed"
    case.decided_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": case.id, "status": case.status, "employee_status": employee.status}


@router.post("/{employee_id}/probation")
def record_probation_decision(
    employee_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    actor: User = Depends(require_hr_manager),
):
    employee = _employee_or_404(db, employee_id)
    if not employee.is_active:
        raise HTTPException(status_code=409, detail="Cannot update probation for an inactive employee")
    decision = payload.get("decision")
    if decision not in {"Confirmed", "Extended"}:
        raise HTTPException(status_code=422, detail="Decision must be Confirmed or Extended")
    extension_days = payload.get("extension_days", 0)
    if decision == "Extended" and (not isinstance(extension_days, int) or not 1 <= extension_days <= 180):
        raise HTTPException(status_code=422, detail="Extension must be between 1 and 180 days")
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if profile is None:
        raise HTTPException(status_code=409, detail="Employee start date is required for probation tracking")
    latest = db.query(LifecycleCase).filter(
        LifecycleCase.employee_id == employee_id,
        LifecycleCase.case_type == "Probation",
    ).order_by(LifecycleCase.created_at.desc()).first()
    if latest and json.loads(latest.changes_json or "{}").get("decision") == "Confirmed":
        raise HTTPException(status_code=409, detail="Probation is already confirmed")
    case = LifecycleCase(
        employee_id=employee_id,
        case_type="Probation",
        status="Recorded",
        effective_date=_today(),
        reason=str(payload.get("notes") or f"Probation {decision.lower()}"),
        changes_json=json.dumps({"decision": decision, "extension_days": extension_days if decision == "Extended" else 0}),
        created_by=actor.email,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(case)
    if decision == "Confirmed":
        employee.status = "Active"
    db.commit()
    return {"id": case.id, "decision": decision, "status": "Recorded"}
