from datetime import date

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.onboarding_task import OnboardingTask

DEFAULT_ONBOARDING_TASKS = [
    ("Employment agreement", "Issue and record signed employment agreement.", "HR"),
    ("Identity and right-to-work check", "Verify required identity documents using the approved secure HR process.", "HR"),
    ("Payroll setup", "Collect payroll and tax details through the approved restricted-access process.", "Payroll"),
    ("Policy acknowledgements", "Review and acknowledge company policies and code of conduct.", "Employee"),
    ("Equipment and workspace", "Arrange equipment, workspace, and building access.", "IT"),
    ("Accounts and access", "Provision least-privilege accounts for required systems.", "IT"),
    ("Manager introduction", "Schedule the first-week plan and manager introduction.", "Manager"),
]


def create_onboarding(db: Session, employee: Employee, profile_fields: dict) -> None:
    start_date = profile_fields.get("start_date") or date.today()
    db.add(EmployeeProfile(employee_id=employee.id, **profile_fields))
    db.add_all([
        OnboardingTask(
            employee_id=employee.id,
            title=title,
            description=description,
            owner=owner,
            status="Not started",
            due_date=start_date,
        )
        for title, description, owner in DEFAULT_ONBOARDING_TASKS
    ])
    db.flush()
