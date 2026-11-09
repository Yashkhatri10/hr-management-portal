from datetime import date, datetime

from pydantic import BaseModel, Field


class EmployeeProfileFields(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    start_date: date = Field(default_factory=date.today)
    employment_type: str = Field(default="Full-time", min_length=1, max_length=40)
    emergency_contact_name: str | None = Field(default=None, max_length=120)
    emergency_contact_relationship: str | None = Field(default=None, max_length=80)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class OnboardingTaskOut(BaseModel):
    id: int
    title: str
    description: str
    owner: str
    status: str
    due_date: date | None
    completed_at: datetime | None


class OnboardingOut(BaseModel):
    employee_id: int
    phone: str | None
    start_date: date | None
    employment_type: str | None
    emergency_contact_name: str | None
    emergency_contact_relationship: str | None
    emergency_contact_phone: str | None
    progress_percent: int
    tasks: list[OnboardingTaskOut]


class OnboardingTaskUpdate(BaseModel):
    status: str
