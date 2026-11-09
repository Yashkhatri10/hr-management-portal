from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_hr_manager
from app.database import get_db
from app.models.leave_request import LeaveRequest
from app.models.employee import Employee
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry
from app.schemas.leave_request import LeaveRequestCreate, LeaveRequestList, LeaveRequestOut
from app.services.paid_leave import business_leave_days, ensure_ledger_current, is_paid_leave_type, ledger_balance, record_paid_leave_debit, reverse_paid_leave_debit
from app.services.notifications import add_notifications, add_notification, user_for_employee, users_for_employee_manager, users_for_hr

router = APIRouter(prefix="/leave", tags=["leave"])


@router.post("", response_model=LeaveRequestOut)
def create_leave_request(payload: LeaveRequestCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    request = LeaveRequest(
        employee_name=user.name,
        employee_email=user.email,
        leave_type=payload.leave_type,
        start_date=payload.start_date.isoformat(),
        end_date=payload.end_date.isoformat(),
        reason=payload.reason,
        status="Pending",
        is_half_day=payload.is_half_day,
    )
    db.add(request)
    db.flush()
    employee = db.query(Employee).filter(Employee.email.ilike(user.email)).first()
    add_notifications(
        db, [*(users_for_employee_manager(db, employee) if employee else []), *users_for_hr(db)],
        notification_type="leave_submitted", title="New leave request",
        message=f"{user.name} submitted a {payload.leave_type} leave request.",
        module="leave", related_record_id=request.id, action_link="/leave",
        event_key=f"leave:submitted:{request.id}",
    )
    db.commit()
    db.refresh(request)
    return {
        "id": request.id,
        "employee_name": request.employee_name,
        "employee_email": request.employee_email,
        "leave_type": request.leave_type,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "reason": request.reason,
        "status": request.status,
        "is_half_day": request.is_half_day,
        "paid_days": request.paid_days or 0,
        "unpaid_days": request.unpaid_days or 0,
    }


@router.get("", response_model=LeaveRequestList)
def list_leave_requests(db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(LeaveRequest)
    if user.role != "HR Manager":
        query = query.filter(LeaveRequest.employee_email == user.email)
    requests = query.order_by(LeaveRequest.start_date.desc()).all()
    return {
        "requests": [
            {
                "id": req.id,
                "employee_name": req.employee_name,
                "employee_email": req.employee_email,
                "leave_type": req.leave_type,
                "start_date": req.start_date,
                "end_date": req.end_date,
                "reason": req.reason,
                "status": req.status,
                "is_half_day": req.is_half_day,
                "paid_days": req.paid_days or 0,
                "unpaid_days": req.unpaid_days or 0,
            }
            for req in requests
        ]
    }


@router.patch("/{request_id}/status")
def update_leave_status(request_id: int, status: str, db: Session = Depends(get_db), actor=Depends(require_hr_manager)):
    if status not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=422, detail="Status must be Approved or Rejected")
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if req.status != "Pending":
        raise HTTPException(status_code=409, detail="Only pending requests can be decided")
    try:
        if status == "Approved":
            record_paid_leave_debit(db, req, actor.email)
            req.approved_at = datetime.now(timezone.utc)
        else:
            req.approved_at = None
        req.status = status
        employee_user = db.query(Employee).filter(Employee.email.ilike(req.employee_email)).first()
        recipient = user_for_employee(db, employee_user)
        if recipient:
            add_notification(
                db, recipient, notification_type=f"leave_{status.lower()}",
                title=f"Leave request {status.lower()}",
                message=f"Your leave request from {req.start_date} to {req.end_date} was {status.lower()}.",
                module="leave", related_record_id=req.id, action_link="/leave",
                event_key=f"leave:{req.id}:{status.lower()}",
            )
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Leave request was already processed concurrently") from exc
    return {"message": "Leave status updated", "id": request_id, "status": status}


@router.get("/{request_id}/allocation-preview")
def leave_allocation_preview(request_id: int, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Leave request not found")
    employee = db.query(Employee).filter(Employee.email == req.employee_email).first()
    if employee is None:
        raise HTTPException(status_code=409, detail="Employee profile not found")
    requested = business_leave_days(req)
    ensure_ledger_current(db)
    available = ledger_balance(db, employee.id)
    paid = min(available, requested) if is_paid_leave_type(db, req.leave_type) else 0
    return {
        "request_id": req.id,
        "requested_days": requested,
        "available_paid_days": available,
        "paid_days": paid,
        "unpaid_days": max(requested - paid, 0),
    }


@router.patch("/{request_id}/cancel")
def cancel_leave_request(request_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if user.role != "HR Manager" and req.employee_email != user.email:
        raise HTTPException(status_code=403, detail="You may only cancel your own leave request")
    if req.status not in {"Pending", "Approved"}:
        raise HTTPException(status_code=409, detail="Only pending or approved leave can be cancelled")
    if req.status == "Approved":
        reverse_paid_leave_debit(db, req, user.email)
    req.status = "Cancelled"
    req.cancelled_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Leave request cancelled; paid leave debit reversed when applicable", "id": request_id, "status": req.status}
