from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_hr_manager
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.onboarding_task import OnboardingTask
from app.models.user import User
from app.schemas.employee import EmployeeOut, EmployeeRegistration, EmployeeUpdate
from app.schemas.onboarding import OnboardingOut, OnboardingTaskUpdate
from app.services.onboarding import create_onboarding
from app.services.paid_leave import today_local

router = APIRouter(tags=["employees"])
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


@router.post("/employees", response_model=EmployeeOut, status_code=201)
def register_employee(payload: EmployeeRegistration, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    email = str(payload.email).strip().lower()
    if db.query(Employee).filter(Employee.email == email).first():
        raise HTTPException(status_code=409, detail="An employee with this email already exists")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    employee = Employee(
        name=payload.name.strip(),
        email=email,
        role=payload.role.strip(),
        department=payload.department.strip(),
        location=payload.location.strip(),
        status="Pending",
        manager=payload.manager.strip(),
    )
    account = User(
        name=employee.name,
        email=email,
        password=pwd_context.hash(payload.password),
        role="Employee",
    )
    db.add_all([employee, account])
    try:
        db.flush()
        # Keep the account-to-employee relationship explicit; email remains
        # only a compatibility fallback for legacy accounts.
        account.employee_id = employee.id
        create_onboarding(
            db,
            employee,
            {
                "phone": payload.phone,
                "start_date": payload.start_date,
                "employment_type": payload.employment_type,
                "emergency_contact_name": payload.emergency_contact_name,
                "emergency_contact_relationship": payload.emergency_contact_relationship,
                "emergency_contact_phone": payload.emergency_contact_phone,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(employee)
    return {
        "id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "role": employee.role,
        "department": employee.department,
        "location": employee.location,
        "status": employee.status,
        "manager": employee.manager,
        "phone": payload.phone,
        "start_date": payload.start_date.isoformat(),
    }


@router.get("/employees")
def get_employees(db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    employees = db.query(Employee).all()
    profiles = {
        profile.employee_id: profile
        for profile in db.query(EmployeeProfile).filter(EmployeeProfile.employee_id.in_([employee.id for employee in employees])).all()
    } if employees else {}
    return {
        "employees": [
            {
                "id": employee.id,
                "name": employee.name,
                "email": employee.email,
                "role": employee.role,
                "department": employee.department,
                "location": employee.location,
                "status": employee.status,
                "manager": employee.manager,
                "phone": profiles[employee.id].phone if employee.id in profiles else None,
                "start_date": profiles[employee.id].start_date if employee.id in profiles else None,
            }
            for employee in employees
        ]
    }


@router.patch("/employees/{employee_id}", response_model=EmployeeOut)
def update_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
    _hr=Depends(require_hr_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")

    required_fields = {"name", "email", "role", "department", "location", "manager", "status", "start_date", "employment_type"}
    for field in required_fields.intersection(updates):
        value = updates[field]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise HTTPException(status_code=422, detail=f"{field.replace('_', ' ').capitalize()} cannot be empty")

    original_email = employee.email
    if "status" in updates and updates["status"] not in {"Active", "On Leave", "Pending", "Inactive"}:
        raise HTTPException(status_code=422, detail="Invalid employee status")

    new_email = str(updates.get("email", employee.email)).strip().lower()
    if new_email != employee.email:
        duplicate_employee = db.query(Employee).filter(Employee.email == new_email, Employee.id != employee_id).first()
        duplicate_user = db.query(User).filter(User.email == new_email, User.email != employee.email).first()
        if duplicate_employee or duplicate_user:
            raise HTTPException(status_code=409, detail="An employee or account with this email already exists")

    profile_fields = {
        "phone",
        "start_date",
        "employment_type",
        "emergency_contact_name",
        "emergency_contact_relationship",
        "emergency_contact_phone",
    }
    profile_updates = {key: updates.pop(key) for key in list(updates) if key in profile_fields}
    if "start_date" in profile_updates and profile_updates["start_date"] is not None:
        from datetime import date

        try:
            profile_updates["start_date"] = date.fromisoformat(profile_updates["start_date"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Start date must be YYYY-MM-DD") from exc

    for field, value in updates.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(employee, field, value)

    account = db.query(User).filter(User.email == original_email).first()
    if account:
        account.email = new_email
        account.name = employee.name
        if "status" in updates:
            account.is_active = updates["status"] != "Inactive"
    if "status" in updates:
        employee.is_active = updates["status"] != "Inactive"

    if profile_updates:
        profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
        if profile is None:
            if "start_date" not in profile_updates:
                from datetime import date

                profile_updates["start_date"] = date.today()
            profile = EmployeeProfile(employee_id=employee_id, **profile_updates)
            db.add(profile)
        else:
            for field, value in profile_updates.items():
                setattr(profile, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(employee)
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    return {
        "id": employee.id,
        "name": employee.name,
        "email": employee.email,
        "role": employee.role,
        "department": employee.department,
        "location": employee.location,
        "status": employee.status,
        "manager": employee.manager,
        "phone": profile.phone if profile else None,
        "start_date": profile.start_date.isoformat() if profile else None,
    }


@router.delete("/employees/{employee_id}")
def archive_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    _hr=Depends(require_hr_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.email == current_user.email:
        raise HTTPException(status_code=409, detail="You cannot archive the account you are currently using")
    if not employee.is_active:
        raise HTTPException(status_code=409, detail="Employee is already archived")

    employee.is_active = False
    employee.status = "Inactive"
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee.id).first()
    if profile and profile.employment_end_date is None:
        profile.employment_end_date = today_local()
    account = db.query(User).filter(User.email == employee.email).first()
    if account:
        account.is_active = False
    db.commit()
    return {"message": "Employee archived; login disabled and historical records preserved", "id": employee_id}


@router.get("/employees/{employee_id}/onboarding", response_model=OnboardingOut)
def get_employee_onboarding(employee_id: int, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    profile = db.query(EmployeeProfile).filter(EmployeeProfile.employee_id == employee_id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="Onboarding profile not found")
    tasks = db.query(OnboardingTask).filter(OnboardingTask.employee_id == employee_id).order_by(OnboardingTask.id).all()
    completed = sum(1 for task in tasks if task.status == "Completed")
    return {
        "employee_id": employee_id,
        "phone": profile.phone,
        "start_date": profile.start_date,
        "employment_type": profile.employment_type,
        "emergency_contact_name": profile.emergency_contact_name,
        "emergency_contact_relationship": profile.emergency_contact_relationship,
        "emergency_contact_phone": profile.emergency_contact_phone,
        "progress_percent": round((completed / len(tasks)) * 100) if tasks else 0,
        "tasks": tasks,
    }


@router.patch("/employees/onboarding/tasks/{task_id}")
def update_onboarding_task(task_id: int, payload: OnboardingTaskUpdate, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    if payload.status not in {"Not started", "In progress", "Completed"}:
        raise HTTPException(status_code=422, detail="Status must be Not started, In progress, or Completed")
    task = db.query(OnboardingTask).filter(OnboardingTask.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Onboarding task not found")
    task.status = payload.status
    task.completed_at = datetime.now(timezone.utc) if payload.status == "Completed" else None
    employee = db.query(Employee).filter(Employee.id == task.employee_id).first()
    all_tasks = db.query(OnboardingTask).filter(OnboardingTask.employee_id == task.employee_id).all()
    if employee and all_tasks and all(item.status == "Completed" for item in all_tasks):
        employee.status = "Active"
    db.commit()
    return {
        "id": task.id,
        "status": task.status,
        "completed_at": task.completed_at,
        "employee_status": employee.status if employee else None,
    }
