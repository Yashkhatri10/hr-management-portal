import json
from datetime import date, datetime, timezone
from fastapi import Query

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import employee_for_user, get_current_user, require_hr_manager
from app.database import get_db
from app.models.employee import Employee
from app.models.employee_360 import DevelopmentPlan, EmployeeDocument, EmployeeGoal
from app.models.attendance import AttendanceRecord
from app.models.leave_request import LeaveRequest
from app.models.performance import (
    EmployeeActivity, EmployeeProgressReport, EmployeeTask, EmployeeTaskComment, EmployeeTaskHistory, PerformanceFeedback,
    PerformanceKPI, PerformanceKPIHistory, PerformanceKRA, PerformanceReview,
)
from app.schemas.performance import (
    ActivityCreate, FeedbackCreate, KPICreate, KPIUpdate, KRACreate,
    KRAProgressUpdate, KPIActualUpdate, ProgressReportCreate, ProgressReportReview,
    ProgressReportUpdate, ReviewCreate, TaskCommentCreate, TaskCreate, TaskUpdate,
)
from app.schemas.employee_360 import (
    DevelopmentPlanCreate, DevelopmentPlanUpdate, DocumentCreate, DocumentUpdate, GoalCreate, GoalUpdate,
)
from app.services.notifications import add_notification, user_for_employee, users_for_employee_manager

router = APIRouter(tags=["performance"])
TASK_STATUSES = {"Not Started", "In Progress", "Pending", "Completed"}


def employee_or_404(db: Session, employee_id: int) -> Employee:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(404, "Employee not found")
    return employee


def can_access(employee: Employee, user, hr_only: bool = False) -> None:
    if hr_only and user.role != "HR Manager":
        raise HTTPException(403, "HR Manager permission required")
    if not hr_only and user.role != "HR Manager":
        if user.employee_id is not None:
            owns_record = user.employee_id == employee.id
        else:
            owns_record = employee.email.lower() == user.email.lower()
        if not owns_record:
            raise HTTPException(403, "You may only access your own performance data")


def output(item):
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    if "metadata_json" in data:
        try:
            data["metadata"] = json.loads(data.pop("metadata_json") or "{}")
        except (TypeError, json.JSONDecodeError):
            data["metadata"] = {}
    return data


def task_output(item):
    data = output(item)
    data["overdue"] = bool(item.due_date and item.due_date < date.today() and item.status != "Completed")
    return data


def task_for_user(db: Session, task_id: int, user) -> EmployeeTask:
    item = db.query(EmployeeTask).filter_by(id=task_id).first()
    if not item:
        raise HTTPException(404, "Task not found")
    can_access(employee_or_404(db, item.employee_id), user)
    return item


def kpi_achievement(kpi: PerformanceKPI, actual: float) -> float:
    """Return a bounded percentage; zero targets cannot produce a divide-by-zero."""
    if kpi.target_value <= 0:
        return 0.0
    return round(max(0.0, min(100.0, actual / kpi.target_value * 100)), 2)


def kpi_employee(db: Session, kpi: PerformanceKPI) -> Employee:
    kra = db.query(PerformanceKRA).filter_by(id=kpi.kra_id).first()
    if not kra:
        raise HTTPException(404, "KPI parent KRA not found")
    return employee_or_404(db, kra.employee_id)


@router.get("/employees/{employee_id}/360")
@router.get("/employees/{employee_id}/employee-360", include_in_schema=False)
@router.get("/employees/{employee_id}/performance", include_in_schema=False)
def employee_360(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id)
    can_access(employee, user)
    activities = db.query(EmployeeActivity).filter_by(employee_id=employee_id).order_by(EmployeeActivity.activity_date.desc()).all()
    tasks = db.query(EmployeeTask).filter_by(employee_id=employee_id).order_by(EmployeeTask.due_date, EmployeeTask.id).all()
    kras = db.query(PerformanceKRA).filter_by(employee_id=employee_id).order_by(PerformanceKRA.period_end.desc()).all()
    reviews = db.query(PerformanceReview).filter_by(employee_id=employee_id).order_by(PerformanceReview.created_at.desc()).all()
    kpis = {kra.id: db.query(PerformanceKPI).filter_by(kra_id=kra.id).all() for kra in kras}
    attendance = db.query(AttendanceRecord).filter(AttendanceRecord.employee_email == employee.email).all()
    leaves = db.query(LeaveRequest).filter(LeaveRequest.employee_email == employee.email).all()
    documents = db.query(EmployeeDocument).filter_by(employee_id=employee_id).order_by(EmployeeDocument.expiry_date).all()
    goals = db.query(EmployeeGoal).filter_by(employee_id=employee_id).order_by(EmployeeGoal.target_date, EmployeeGoal.id).all()
    plans = db.query(DevelopmentPlan).filter_by(employee_id=employee_id).order_by(DevelopmentPlan.target_date, DevelopmentPlan.id).all()
    leave_counts = {status: sum(item.status == status for item in leaves) for status in ("Pending", "Approved", "Rejected", "Cancelled")}
    attendance_present = sum(item.status in {"Present", "Late"} for item in attendance)
    return {
        "employee": {"id": employee.id, "name": employee.name, "email": employee.email, "role": employee.role,
                     "department": employee.department, "manager": employee.manager, "status": employee.status},
        "activities": [output(item) for item in activities],
        "tasks": [task_output(item) for item in tasks],
        "kras": [{**output(kra), "kpis": [output(kpi) for kpi in kpis[kra.id]]} for kra in kras],
        "reviews": [{**output(item), "feedback": [output(feedback) for feedback in db.query(PerformanceFeedback).filter_by(review_id=item.id).all()]} for item in reviews],
        "attendance": {
            "records_count": len(attendance), "present": attendance_present,
            "late": sum(item.status == "Late" for item in attendance),
            "absent": sum(item.status == "Absent" for item in attendance),
            "attendance_rate": round(attendance_present / len(attendance) * 100, 2) if attendance else 0,
        },
        "leave": {"request_count": len(leaves), "status_counts": leave_counts,
                  "approved_days": float(sum((item.paid_days or 0) for item in leaves if item.status == "Approved"))},
        "goals": [output(item) for item in goals],
        "development_plans": [output(item) for item in plans],
        "documents": [output(item) for item in documents],
        "summary": performance_summary(kras, reviews, tasks, kpis),
    }


@router.get("/me/360")
def my_employee_360(db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    return employee_360(employee.id, db, user)


@router.get("/employees/{employee_id}/360/summary")
def employee_360_summary(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Stable, export-friendly aggregate without attendance location or document contents."""
    data = employee_360(employee_id, db, user)
    return {
        "employee": data["employee"],
        "summary": data["summary"],
        "attendance": data["attendance"],
        "leave": data["leave"],
        "goals": data["goals"],
        "development_plans": data["development_plans"],
        "documents": data["documents"],
    }


def performance_summary(kras, reviews, tasks, kpis_by_kra):
    scores = [kpi.score for kpis in kpis_by_kra.values() for kpi in kpis if kpi.score is not None]
    review_scores = [r.overall_score for r in reviews if r.overall_score is not None]
    status_counts = {status: sum(task.status == status for task in tasks) for status in sorted(TASK_STATUSES)}
    completed = status_counts["Completed"]
    return {
        "kra_count": len(kras), "kpi_count": sum(len(items) for items in kpis_by_kra.values()),
        "average_kpi_score": round(sum(scores) / len(scores), 2) if scores else None,
        "average_review_score": round(sum(review_scores) / len(review_scores), 2) if review_scores else None,
        "open_tasks": len(tasks) - completed,
        "completed_tasks": completed,
        "task_status_counts": status_counts,
        "status_counts": status_counts,
        "task_completion_percentage": round(completed / len(tasks) * 100, 2) if tasks else 0,
        "completion_percentage": round(completed / len(tasks) * 100, 2) if tasks else 0,
        "overdue_tasks": sum(task.due_date is not None and task.due_date < date.today() and task.status != "Completed" for task in tasks),
    }


def _save_360_item(db, item, payload, user):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return output(item)


@router.post("/employees/{employee_id}/goals", status_code=201)
def create_goal(employee_id: int, payload: GoalCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id)
    can_access(employee, user)
    item = EmployeeGoal(employee_id=employee_id, created_by=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.patch("/goals/{goal_id}")
def update_goal(goal_id: int, payload: GoalUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(EmployeeGoal).filter_by(id=goal_id).first()
    if not item: raise HTTPException(404, "Goal not found")
    can_access(employee_or_404(db, item.employee_id), user)
    return _save_360_item(db, item, payload, user)


@router.get("/employees/{employee_id}/goals")
def list_goals(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    return {"goals": [output(x) for x in db.query(EmployeeGoal).filter_by(employee_id=employee_id).all()]}


@router.post("/employees/{employee_id}/development-plans", status_code=201)
def create_development_plan(employee_id: int, payload: DevelopmentPlanCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    item = DevelopmentPlan(employee_id=employee_id, created_by=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.patch("/development-plans/{plan_id}")
def update_development_plan(plan_id: int, payload: DevelopmentPlanUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(DevelopmentPlan).filter_by(id=plan_id).first()
    if not item: raise HTTPException(404, "Development plan not found")
    can_access(employee_or_404(db, item.employee_id), user)
    return _save_360_item(db, item, payload, user)


@router.get("/employees/{employee_id}/development-plans")
def list_development_plans(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    return {"development_plans": [output(x) for x in db.query(DevelopmentPlan).filter_by(employee_id=employee_id).all()]}


@router.post("/employees/{employee_id}/documents", status_code=201)
def create_document(employee_id: int, payload: DocumentCreate, db: Session = Depends(get_db), user=Depends(require_hr_manager)):
    employee_or_404(db, employee_id)
    item = EmployeeDocument(employee_id=employee_id, created_by=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.get("/employees/{employee_id}/documents")
def list_documents(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id)
    can_access(employee, user)
    return {"documents": [output(x) for x in db.query(EmployeeDocument).filter_by(employee_id=employee_id).order_by(EmployeeDocument.expiry_date).all()]}


@router.patch("/documents/{document_id}")
def update_document(document_id: int, payload: DocumentUpdate, db: Session = Depends(get_db), user=Depends(require_hr_manager)):
    item = db.query(EmployeeDocument).filter_by(id=document_id).first()
    if not item: raise HTTPException(404, "Document not found")
    return _save_360_item(db, item, payload, user)


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    item = db.query(EmployeeDocument).filter_by(id=document_id).first()
    if not item: raise HTTPException(404, "Document not found")
    db.delete(item); db.commit()
    return {"message": "Document metadata deleted", "id": document_id}


@router.get("/employees/{employee_id}/activities")
def list_activities(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    return {"activities": [output(x) for x in db.query(EmployeeActivity).filter_by(employee_id=employee_id).order_by(EmployeeActivity.activity_date.desc()).all()]}


@router.post("/employees/{employee_id}/activities", status_code=201)
def add_activity(employee_id: int, payload: ActivityCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    item = EmployeeActivity(employee_id=employee_id, actor_email=user.email, activity_type=payload.activity_type,
                            title=payload.title, description=payload.description, activity_date=payload.activity_date,
                            metadata_json=json.dumps(payload.metadata or {}))
    db.add(item)
    db.flush()
    manager_users = users_for_employee_manager(db, employee)
    for recipient in manager_users:
        add_notification(
            db, recipient, notification_type="activity_submitted", title="New activity report",
            message=f"{employee.name} submitted activity: {payload.title}.", module="tasks",
            related_record_id=item.id, action_link="/progress-reports",
            event_key=f"activity:{item.id}:submitted:{recipient.id}",
        )
    db.commit(); db.refresh(item)
    return output(item)


@router.get("/employees/{employee_id}/tasks")
def list_tasks(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    return {"tasks": [task_output(x) for x in db.query(EmployeeTask).filter_by(employee_id=employee_id).order_by(EmployeeTask.due_date, EmployeeTask.id).all()]}


@router.post("/employees/{employee_id}/tasks", status_code=201)
def add_task(employee_id: int, payload: TaskCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id)
    if user.role != "HR Manager":
        mapped = employee_for_user(db, user)
        if mapped is None or mapped.id != employee.id:
            raise HTTPException(403, "You may only create tasks for yourself")
    if payload.priority not in {"Low", "Medium", "High", "Urgent"}: raise HTTPException(422, "Invalid priority")
    item = EmployeeTask(employee_id=employee_id, assigned_by=user.email, **payload.model_dump())
    db.add(item); db.flush()
    assigned_user = user_for_employee(db, employee)
    if assigned_user:
        add_notification(
            db, assigned_user, notification_type="task_assigned", title="Task assigned",
            message=f"You were assigned the task '{item.title}'.", module="tasks",
            related_record_id=item.id, action_link="/my-360",
            event_key=f"task:{item.id}:assigned:{assigned_user.id}",
        )
    db.add(EmployeeTaskHistory(task_id=item.id, actor_email=user.email, status=item.status,
                               progress_percentage=item.progress_percentage, progress_notes=item.progress_notes))
    db.commit(); db.refresh(item)
    return task_output(item)


@router.patch("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = task_for_user(db, task_id, user)
    changes = payload.model_dump(exclude_unset=True)
    comment = changes.pop("comment", None)
    if not changes and comment is None:
        raise HTTPException(422, "At least one task field is required")
    if payload.status is not None and payload.status not in TASK_STATUSES:
        raise HTTPException(422, "Status must be Not Started, In Progress, Pending, or Completed")
    previous = (item.status, item.progress_percentage, item.progress_notes)
    for key, value in changes.items():
        setattr(item, key, value)
    if payload.status is not None:
        item.completed_at = datetime.now(timezone.utc) if payload.status == "Completed" else None
    if payload.progress_percentage == 100 and payload.status is None:
        item.status = "Completed"
        item.completed_at = datetime.now(timezone.utc)
    db.add(EmployeeActivity(
        employee_id=item.employee_id,
        actor_email=user.email,
        activity_type="task_update",
        title=f"Updated task: {item.title}",
        description=item.progress_notes,
    ))
    if previous != (item.status, item.progress_percentage, item.progress_notes):
        db.add(EmployeeTaskHistory(task_id=item.id, actor_email=user.email, status=item.status,
                                   progress_percentage=item.progress_percentage, progress_notes=item.progress_notes))
    if comment is not None:
        db.add(EmployeeTaskComment(task_id=item.id, author_email=user.email, comment=comment))
    assigned_user = user_for_employee(db, employee_or_404(db, item.employee_id))
    if assigned_user and assigned_user.id != user.id:
        add_notification(
            db, assigned_user, notification_type="task_updated", title="Task updated",
            message=f"The task '{item.title}' was updated to {item.status}.", module="tasks",
            related_record_id=item.id, action_link="/my-360",
            event_key=f"task:{item.id}:updated:{item.status}:{item.progress_percentage}:{assigned_user.id}",
        )
    if item.status == "Completed":
        manager_users = users_for_employee_manager(db, employee_or_404(db, item.employee_id))
        for recipient in manager_users:
            add_notification(
                db, recipient, notification_type="task_completed", title="Task completed",
                message=f"{user.email} completed the task '{item.title}'.", module="tasks",
                related_record_id=item.id, action_link="/progress-reports",
                event_key=f"task:{item.id}:completed:{recipient.id}",
            )
    db.commit(); db.refresh(item)
    return task_output(item)


@router.get("/tasks/{task_id}/history")
def task_history(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task_for_user(db, task_id, user)
    rows = db.query(EmployeeTaskHistory).filter_by(task_id=task_id).order_by(
        EmployeeTaskHistory.recorded_at.desc(), EmployeeTaskHistory.id.desc()).all()
    return {"history": [output(row) for row in rows]}


@router.get("/tasks/{task_id}/comments")
def list_task_comments(task_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task_for_user(db, task_id, user)
    rows = db.query(EmployeeTaskComment).filter_by(task_id=task_id).order_by(
        EmployeeTaskComment.created_at.asc(), EmployeeTaskComment.id.asc()).all()
    return {"comments": [output(row) for row in rows]}


@router.post("/tasks/{task_id}/comments", status_code=201)
def add_task_comment(task_id: int, payload: TaskCommentCreate, db: Session = Depends(get_db),
                     user=Depends(get_current_user)):
    task_for_user(db, task_id, user)
    item = EmployeeTaskComment(task_id=task_id, author_email=user.email, comment=payload.comment)
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.get("/employees/{employee_id}/kras")
def list_kras(employee_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id); can_access(employee, user)
    result = []
    for kra in db.query(PerformanceKRA).filter_by(employee_id=employee_id).order_by(PerformanceKRA.period_end.desc()).all():
        result.append({**output(kra), "kpis": [output(kpi) for kpi in db.query(PerformanceKPI).filter_by(kra_id=kra.id).all()]})
    return {"kras": result}


@router.post("/employees/{employee_id}/kras", status_code=201)
def add_kra(employee_id: int, payload: KRACreate, db: Session = Depends(get_db), user=Depends(require_hr_manager)):
    employee_or_404(db, employee_id)
    if payload.period_end < payload.period_start: raise HTTPException(422, "period_end cannot precede period_start")
    item = PerformanceKRA(employee_id=employee_id, created_by=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.post("/kras/{kra_id}/kpis", status_code=201)
def add_kpi(kra_id: int, payload: KPICreate, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    if not db.query(PerformanceKRA).filter_by(id=kra_id).first(): raise HTTPException(404, "KRA not found")
    item = PerformanceKPI(kra_id=kra_id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.patch("/kras/{kra_id}/progress")
def update_kra_progress(kra_id: int, payload: KRAProgressUpdate, db: Session = Depends(get_db),
                        user=Depends(get_current_user)):
    kra = db.query(PerformanceKRA).filter_by(id=kra_id).first()
    if not kra:
        raise HTTPException(404, "KRA not found")
    employee = employee_or_404(db, kra.employee_id)
    can_access(employee, user)
    if payload.status is not None and payload.status not in {"Active", "On Track", "At Risk", "Completed"}:
        raise HTTPException(422, "Invalid KRA status")
    kra.progress_percentage = payload.progress_percentage
    kra.progress_notes = payload.progress_notes
    if payload.status is not None:
        kra.status = payload.status
    db.add(EmployeeActivity(
        employee_id=kra.employee_id,
        actor_email=user.email,
        activity_type="kra_progress",
        title=f"Updated KRA: {kra.title}",
        description=payload.progress_notes,
    ))
    db.commit()
    db.refresh(kra)
    return output(kra)


@router.patch("/kpis/{kpi_id}")
def update_kpi(kpi_id: int, payload: KPIUpdate, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    item = db.query(PerformanceKPI).filter_by(id=kpi_id).first()
    if not item: raise HTTPException(404, "KPI not found")
    changes = payload.model_dump(exclude_unset=True)
    notes = changes.pop("actual_notes", None)
    old_actual = item.actual_value
    for key, value in changes.items(): setattr(item, key, value)
    if "actual_value" in changes and changes["actual_value"] != old_actual:
        item.score = kpi_achievement(item, changes["actual_value"])
        db.add(PerformanceKPIHistory(kpi_id=item.id, actual_value=changes["actual_value"],
                                      achievement_percentage=item.score, notes=notes, recorded_by=_hr.email))
    db.commit(); db.refresh(item)
    return output(item)


def record_kpi_actual(kpi_id: int, payload: KPIActualUpdate, db: Session, user):
    item = db.query(PerformanceKPI).filter_by(id=kpi_id).first()
    if not item:
        raise HTTPException(404, "KPI not found")
    employee = kpi_employee(db, item)
    can_access(employee, user)
    item.actual_value = payload.actual_value
    item.score = kpi_achievement(item, payload.actual_value)
    db.add(PerformanceKPIHistory(kpi_id=item.id, actual_value=payload.actual_value,
                                 achievement_percentage=item.score, notes=payload.notes,
                                 recorded_by=user.email))
    db.commit(); db.refresh(item)
    return {**output(item), "achievement_percentage": item.score}


@router.patch("/me/kpis/{kpi_id}/actual")
def update_my_kpi_actual(kpi_id: int, payload: KPIActualUpdate, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    return record_kpi_actual(kpi_id, payload, db, user)


@router.patch("/employees/{employee_id}/kpis/{kpi_id}/actual")
def update_employee_kpi_actual(employee_id: int, kpi_id: int, payload: KPIActualUpdate,
                               db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(PerformanceKPI).filter_by(id=kpi_id).first()
    if not item or kpi_employee(db, item).id != employee_id:
        raise HTTPException(404, "KPI not found")
    return record_kpi_actual(kpi_id, payload, db, user)


@router.get("/kpis/{kpi_id}/history")
def kpi_history(kpi_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(PerformanceKPI).filter_by(id=kpi_id).first()
    if not item:
        raise HTTPException(404, "KPI not found")
    can_access(kpi_employee(db, item), user)
    rows = db.query(PerformanceKPIHistory).filter_by(kpi_id=kpi_id).order_by(
        PerformanceKPIHistory.recorded_at.desc()).all()
    return {"history": [output(row) for row in rows]}


@router.get("/me/kpis")
def list_my_kpis(db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    kras = db.query(PerformanceKRA).filter_by(employee_id=employee.id).all()
    kpis = [kpi for kra in kras for kpi in db.query(PerformanceKPI).filter_by(kra_id=kra.id).all()]
    return {"kpis": [output(kpi) for kpi in kpis]}


@router.get("/employees/{employee_id}/kpis/{kpi_id}/history")
def employee_kpi_history(employee_id: int, kpi_id: int, db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    item = db.query(PerformanceKPI).filter_by(id=kpi_id).first()
    if not item or kpi_employee(db, item).id != employee_id:
        raise HTTPException(404, "KPI not found")
    return kpi_history(kpi_id, db, user)


REPORT_STATUSES = {"Draft", "Submitted", "Under Review", "Reviewed"}
REPORT_PERIODS = {"Weekly", "Monthly"}


def report_for_user(db: Session, report_id: int, user):
    report = db.query(EmployeeProgressReport).filter_by(id=report_id).first()
    if not report:
        raise HTTPException(404, "Progress report not found")
    employee = employee_or_404(db, report.employee_id)
    can_access(employee, user)
    return report


@router.get("/me/progress-reports")
def list_my_progress_reports(db: Session = Depends(get_db), user=Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    rows = db.query(EmployeeProgressReport).filter_by(employee_id=employee.id).order_by(
        EmployeeProgressReport.period_start.desc()).all()
    return {"reports": [output(row) for row in rows]}


@router.post("/me/progress-reports", status_code=201)
def create_my_progress_report(payload: ProgressReportCreate, db: Session = Depends(get_db),
                              user=Depends(get_current_user)):
    employee = employee_for_user(db, user)
    if employee is None:
        raise HTTPException(404, "No employee record is linked to this account")
    if payload.period_type not in REPORT_PERIODS or payload.period_end < payload.period_start:
        raise HTTPException(422, "Use Weekly or Monthly and a valid period")
    item = EmployeeProgressReport(employee_id=employee.id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.patch("/me/progress-reports/{report_id}")
def update_my_progress_report(report_id: int, payload: ProgressReportUpdate,
                              db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = report_for_user(db, report_id, user)
    if item.status != "Draft":
        raise HTTPException(409, "Only draft reports can be edited")
    changes = payload.model_dump(exclude_unset=True)
    if "period_type" in changes and changes["period_type"] not in REPORT_PERIODS:
        raise HTTPException(422, "Use Weekly or Monthly")
    for key, value in changes.items(): setattr(item, key, value)
    if item.period_end < item.period_start:
        raise HTTPException(422, "period_end cannot precede period_start")
    db.commit(); db.refresh(item)
    return output(item)


@router.post("/me/progress-reports/{report_id}/submit")
def submit_my_progress_report(report_id: int, db: Session = Depends(get_db),
                              user=Depends(get_current_user)):
    item = report_for_user(db, report_id, user)
    if item.status != "Draft":
        raise HTTPException(409, "Only draft reports can be submitted")
    item.status = "Submitted"
    db.commit(); db.refresh(item)
    return output(item)


@router.get("/employees/{employee_id}/progress-reports")
def list_employee_progress_reports(employee_id: int, db: Session = Depends(get_db),
                                   user=Depends(get_current_user)):
    employee = employee_or_404(db, employee_id)
    can_access(employee, user)
    rows = db.query(EmployeeProgressReport).filter_by(employee_id=employee_id).order_by(
        EmployeeProgressReport.period_start.desc()).all()
    return {"reports": [output(row) for row in rows]}


@router.patch("/progress-reports/{report_id}/review")
def review_progress_report(report_id: int, payload: ProgressReportReview,
                           db: Session = Depends(get_db), user=Depends(require_hr_manager)):
    item = db.query(EmployeeProgressReport).filter_by(id=report_id).first()
    if not item:
        raise HTTPException(404, "Progress report not found")
    if payload.status not in {"Under Review", "Reviewed"}:
        raise HTTPException(422, "Status must be Under Review or Reviewed")
    item.status = payload.status
    item.review_feedback = payload.review_feedback
    item.reviewer_email = user.email
    db.commit(); db.refresh(item)
    return output(item)


@router.get("/reports/progress")
def progress_reports_report(
    employee_id: int | None = Query(default=None),
    department: str | None = Query(default=None),
    status: str | None = Query(default=None),
    period_type: str | None = Query(default=None),
    period_start: date | None = Query(default=None),
    period_end: date | None = Query(default=None),
    db: Session = Depends(get_db),
    _hr=Depends(require_hr_manager),
):
    query = db.query(EmployeeProgressReport, Employee).join(Employee, Employee.id == EmployeeProgressReport.employee_id)
    if employee_id is not None:
        query = query.filter(EmployeeProgressReport.employee_id == employee_id)
    if department is not None:
        query = query.filter(Employee.department == department)
    if status is not None:
        if status not in REPORT_STATUSES:
            raise HTTPException(422, "Invalid progress report status")
        query = query.filter(EmployeeProgressReport.status == status)
    if period_type is not None:
        if period_type not in REPORT_PERIODS:
            raise HTTPException(422, "Use Weekly or Monthly")
        query = query.filter(EmployeeProgressReport.period_type == period_type)
    if period_start is not None:
        query = query.filter(EmployeeProgressReport.period_start >= period_start)
    if period_end is not None:
        query = query.filter(EmployeeProgressReport.period_end <= period_end)
    rows = query.order_by(EmployeeProgressReport.period_start.desc(), EmployeeProgressReport.id.desc()).all()
    return {"reports": [{**output(report), "employee": {"id": employee.id, "name": employee.name,
                                                        "email": employee.email, "department": employee.department}}
                        for report, employee in rows]}


@router.post("/employees/{employee_id}/reviews", status_code=201)
def add_review(employee_id: int, payload: ReviewCreate, db: Session = Depends(get_db), user=Depends(require_hr_manager)):
    employee_or_404(db, employee_id)
    item = PerformanceReview(employee_id=employee_id, reviewer_email=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.post("/reviews/{review_id}/feedback", status_code=201)
def add_feedback(review_id: int, payload: FeedbackCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    review = db.query(PerformanceReview).filter_by(id=review_id).first()
    if not review: raise HTTPException(404, "Review not found")
    if review.reviewer_email == user.email: raise HTTPException(409, "Reviewer cannot submit their own 360 feedback")
    item = PerformanceFeedback(review_id=review_id, reviewer_email=user.email, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item)
    return output(item)


@router.get("/reports/performance")
def performance_report(db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    rows = []
    for employee in db.query(Employee).filter(Employee.is_active.is_(True)).order_by(Employee.name).all():
        kras = db.query(PerformanceKRA).filter_by(employee_id=employee.id).all()
        kpis = [kpi for kra in kras for kpi in db.query(PerformanceKPI).filter_by(kra_id=kra.id).all()]
        reviews = db.query(PerformanceReview).filter_by(employee_id=employee.id).all()
        scores = [x.score for x in kpis if x.score is not None]
        review_scores = [x.overall_score for x in reviews if x.overall_score is not None]
        tasks = db.query(EmployeeTask).filter_by(employee_id=employee.id).all()
        summary = performance_summary(kras, reviews, tasks, {kra.id: [kpi for kpi in kpis if kpi.kra_id == kra.id] for kra in kras})
        rows.append({"employee_id": employee.id, "employee_name": employee.name, "department": employee.department,
                     "kra_count": len(kras), "kpi_count": len(kpis), "average_kpi_score": round(sum(scores)/len(scores), 2) if scores else None,
                     "average_review_score": round(sum(review_scores)/len(review_scores), 2) if review_scores else None,
                     "open_tasks": summary["open_tasks"], "completed_tasks": summary["completed_tasks"],
                     "task_status_counts": summary["task_status_counts"],
                     "task_completion_percentage": summary["task_completion_percentage"],
                     "overdue_tasks": summary["overdue_tasks"]})
    return {"employees": rows, "totals": {"employees": len(rows), "kras": sum(x["kra_count"] for x in rows), "kpis": sum(x["kpi_count"] for x in rows)}}
