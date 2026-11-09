import os
import secrets
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import employee_for_user, get_current_user, require_hr_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.onboarding import OnboardingDocument, OnboardingNotification, OnboardingRecord, OnboardingTemplate, OnboardingTemplateItem
from app.models.onboarding_task import OnboardingTask
from app.models.user import User
from app.schemas.onboarding_module import DocumentDecision, OnboardingRecordCreate, OnboardingTaskEdit, TemplateCreate, TemplateItemCreate
from app.services.notifications import add_notification, user_for_employee

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
UPLOAD_ROOT = Path(os.getenv("ONBOARDING_UPLOAD_DIR", "uploads/onboarding"))
ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def _employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(404, "Employee not found")
    return employee


def _record(db: Session, employee_id: int) -> OnboardingRecord:
    item = db.query(OnboardingRecord).filter_by(employee_id=employee_id).first()
    if item is None:
        item = OnboardingRecord(employee_id=employee_id, status="In Progress")
        db.add(item)
        db.flush()
    return item


def _summary(db: Session, employee_id: int) -> dict:
    tasks = db.query(OnboardingTask).filter_by(employee_id=employee_id).all()
    mandatory = [task for task in tasks if getattr(task, "mandatory", True)]
    completed = sum(task.status == "Completed" for task in mandatory)
    docs = db.query(OnboardingDocument).filter_by(employee_id=employee_id).all()
    record = _record(db, employee_id)
    overdue = sum(bool(task.due_date and task.due_date < date.today() and task.status != "Completed") for task in tasks)
    return {
        "status": record.status,
        "progress_percent": round(completed / len(mandatory) * 100) if mandatory else 0,
        "mandatory_pending": sum(task.status != "Completed" for task in mandatory),
        "overdue_tasks": overdue,
        "documents_pending": sum(doc.status != "Verified" for doc in docs),
        "documents": docs,
        "tasks": tasks,
        "record": record,
    }


def _notify(db: Session, employee: Employee, message: str, event_key: str, link: str = "/onboarding") -> None:
    if not db.query(OnboardingNotification).filter_by(event_key=event_key).first():
        db.add(OnboardingNotification(employee_id=employee.id, recipient_email=employee.email, message=message, link=link, event_key=event_key))


@router.get("/dashboard")
def onboarding_dashboard(db: Session = Depends(get_db), _hr: User = Depends(require_hr_manager)):
    employees = db.query(Employee).all()
    rows = []
    for employee in employees:
        data = _summary(db, employee.id)
        record = data["record"]
        rows.append({"employee_id": employee.id, "employee_name": employee.name, "email": employee.email, "department": employee.department, "designation": employee.role, "joining_date": record.onboarding_start_date, "status": data["status"], "progress_percent": data["progress_percent"], "mandatory_pending": data["mandatory_pending"], "documents_pending": data["documents_pending"], "overdue_tasks": data["overdue_tasks"], "deadline": record.deadline})
    db.commit()
    return {"summary": {"total": len(rows), "preboarding": sum(row["status"] == "Pre-boarding" for row in rows), "in_progress": sum(row["status"] == "In Progress" for row in rows), "completed": sum(row["status"] == "Completed" for row in rows), "pending_documents": sum(row["documents_pending"] > 0 for row in rows), "overdue_tasks": sum(row["overdue_tasks"] for row in rows)}, "employees": rows}


@router.get("/me")
def my_onboarding(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    return onboarding_details(employee.id, db, user)


@router.post("/templates", status_code=201)
def create_template(payload: TemplateCreate, db: Session = Depends(get_db), actor: User = Depends(require_hr_manager)):
    if db.query(OnboardingTemplate).filter_by(name=payload.name.strip()).first():
        raise HTTPException(409, "Template name already exists")
    item = OnboardingTemplate(name=payload.name.strip(), description=payload.description, created_by=actor.email)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "name": item.name, "description": item.description}


@router.get("/{employee_id}")
def onboarding_details(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = _employee_or_404(db, employee_id)
    linked_employee = employee_for_user(db, user)
    if user.role != "HR Manager" and (linked_employee is None or linked_employee.id != employee_id):
        raise HTTPException(403, "You may only access your own onboarding")
    data = _summary(db, employee_id)
    db.commit()
    return {"employee": {"id": employee.id, "name": employee.name, "email": employee.email, "department": employee.department, "designation": employee.role}, "status": data["status"], "progress_percent": data["progress_percent"], "mandatory_pending": data["mandatory_pending"], "overdue_tasks": data["overdue_tasks"], "record": data["record"], "tasks": data["tasks"], "documents": data["documents"]}


@router.post("/{employee_id}", status_code=201)
def create_or_update_onboarding(employee_id: int, payload: OnboardingRecordCreate, db: Session = Depends(get_db), actor: User = Depends(require_hr_manager)):
    employee = _employee_or_404(db, employee_id)
    record = _record(db, employee_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    if record.status == "Draft":
        record.status = "Pre-boarding"
    _notify(db, employee, "Your onboarding record has been created or updated.", f"record:{record.id}:{record.status}:{record.deadline}")
    db.commit()
    return {"id": record.id, "employee_id": employee_id, "status": record.status}


@router.post("/templates/{template_id}/items", status_code=201)
def add_template_item(template_id: int, payload: TemplateItemCreate, db: Session = Depends(get_db), _hr: User = Depends(require_hr_manager)):
    template = db.query(OnboardingTemplate).filter_by(id=template_id).first()
    if template is None:
        raise HTTPException(404, "Template not found")
    item = OnboardingTemplateItem(template_id=template_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{employee_id}/templates/{template_id}/assign")
def assign_template(employee_id: int, template_id: int, db: Session = Depends(get_db), actor: User = Depends(require_hr_manager)):
    employee = _employee_or_404(db, employee_id)
    template = db.query(OnboardingTemplate).filter_by(id=template_id, is_active=True).first()
    if template is None:
        raise HTTPException(404, "Active template not found")
    record = _record(db, employee_id)
    from app.models.employee_profile import EmployeeProfile
    profile = db.query(EmployeeProfile).filter_by(employee_id=employee_id).first()
    base = profile.start_date if profile else date.today()
    for item in db.query(OnboardingTemplateItem).filter_by(template_id=template_id).order_by(OnboardingTemplateItem.sort_order).all():
        due = base.fromordinal(base.toordinal() + item.due_days) if item.due_days is not None else None
        db.add(OnboardingTask(employee_id=employee_id, title=item.title, description=item.description, owner=item.owner, status="Not started", due_date=due, mandatory=item.mandatory))
    record.status = "In Progress"
    _notify(db, employee, f"Onboarding template '{template.name}' assigned.", f"template:{employee_id}:{template_id}")
    employee_user = user_for_employee(db, employee)
    if employee_user:
        add_notification(
            db, employee_user, notification_type="onboarding_task_assigned",
            title="New onboarding tasks", message=f"Your onboarding template '{template.name}' is ready.",
            module="onboarding", action_link="/my-onboarding",
            event_key=f"onboarding:template:{employee_id}:{template_id}:{employee_user.id}",
        )
    db.commit()
    return {"status": record.status}


@router.patch("/tasks/{task_id}")
def edit_task(task_id: int, payload: OnboardingTaskEdit, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    task = db.query(OnboardingTask).filter_by(id=task_id).first()
    if task is None:
        raise HTTPException(404, "Onboarding task not found")
    employee = _employee_or_404(db, task.employee_id)
    if user.role != "HR Manager" and (employee_for_user(db, user) is None or employee_for_user(db, user).id != task.employee_id):
        raise HTTPException(403, "You may only update your own onboarding tasks")
    if payload.status not in {"Not started", "In progress", "Pending Verification", "Completed", "Rejected"}:
        raise HTTPException(422, "Unsupported onboarding task status")
    if user.role != "HR Manager" and task.owner.casefold() not in {"employee", "self"}:
        raise HTTPException(403, "This task is managed by HR or another team")
    task.status = payload.status
    task.comments = payload.comments
    task.updated_by = user.email
    task.updated_at = datetime.now(timezone.utc)
    if payload.status == "Completed":
        task.completed_at = datetime.now(timezone.utc)
    else:
        task.completed_at = None
    data = _summary(db, task.employee_id)
    if data["mandatory_pending"] == 0 and data["documents_pending"] == 0:
        data["record"].status = "Completed"
        data["record"].completed_at = datetime.now(timezone.utc)
        data["record"].completed_by = user.email
        employee.status = "Active"
        _notify(db, employee, "All mandatory onboarding requirements are complete.", f"complete:{employee.id}")
    db.commit()
    return {"id": task.id, "status": task.status, "onboarding_status": data["record"].status}


@router.post("/me/documents", status_code=201)
async def upload_my_document(title: str, document_type: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    return await upload_document(employee.id, title, document_type, file, db, user)


@router.post("/{employee_id}/documents", status_code=201)
async def upload_document(employee_id: int, title: str, document_type: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = _employee_or_404(db, employee_id)
    if user.role != "HR Manager" and (employee_for_user(db, user) is None or employee_for_user(db, user).id != employee_id):
        raise HTTPException(403, "You may only upload your own onboarding documents")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(422, "Only PDF, JPG, JPEG, and PNG documents are allowed")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Document must be 10 MB or smaller")
    storage_name = f"{employee_id}-{secrets.token_urlsafe(16)}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    (UPLOAD_ROOT / storage_name).write_bytes(content)
    item = OnboardingDocument(employee_id=employee_id, title=title.strip(), document_type=document_type.strip(), filename=file.filename or "document", storage_name=storage_name, uploaded_by=user.email)
    db.add(item)
    _notify(db, employee, f"New onboarding document uploaded: {title}", f"document:{employee_id}:{storage_name}")
    db.commit()
    return {"id": item.id, "status": item.status, "title": item.title}


@router.patch("/documents/{document_id}")
def decide_document(document_id: int, payload: DocumentDecision, db: Session = Depends(get_db), actor: User = Depends(require_hr_manager)):
    item = db.query(OnboardingDocument).filter_by(id=document_id).first()
    if item is None:
        raise HTTPException(404, "Onboarding document not found")
    if payload.status not in {"Verified", "Rejected", "Resubmission Required"}:
        raise HTTPException(422, "Status must be Verified, Rejected, or Resubmission Required")
    if payload.status != "Verified" and not payload.rejection_reason:
        raise HTTPException(422, "A rejection reason is required")
    item.status = payload.status
    item.rejection_reason = payload.rejection_reason
    item.verified_by = actor.email
    item.verified_at = datetime.now(timezone.utc)
    employee = _employee_or_404(db, item.employee_id)
    _notify(db, employee, f"Your document '{item.title}' was marked {payload.status}.", f"document-decision:{item.id}:{payload.status}")
    employee_user = user_for_employee(db, employee)
    if employee_user:
        add_notification(
            db, employee_user, notification_type="onboarding_document",
            title=f"Onboarding document {payload.status.lower()}",
            message=f"Your document '{item.title}' was marked {payload.status.lower()}.",
            module="onboarding", related_record_id=item.id, action_link="/my-onboarding",
            event_key=f"onboarding:document:{item.id}:{payload.status}:{employee_user.id}",
        )
    db.commit()
    return {"id": item.id, "status": item.status}


@router.get("/me/notifications")
def my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        return {"notifications": []}
    return {"notifications": db.query(OnboardingNotification).filter_by(employee_id=employee.id).order_by(OnboardingNotification.created_at.desc()).limit(50).all()}
