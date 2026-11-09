from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.employee_status import EmployeeStatusEventOut


class LifecycleCaseCreate(BaseModel):
    case_type: Literal["Transfer", "Promotion", "Resignation"]
    effective_date: date
    reason: str = Field(min_length=3, max_length=2000)
    department: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    manager: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    new_salary: str | None = Field(default=None, max_length=40)
    last_working_date: date | None = None

    @model_validator(mode="after")
    def require_changes_for_job_move(self):
        if self.case_type in {"Transfer", "Promotion"} and not any((self.department, self.location, self.manager, self.role, self.new_salary)):
            raise ValueError("Provide at least one proposed change for a transfer or promotion")
        if self.case_type == "Resignation" and self.last_working_date is not None and self.last_working_date < self.effective_date:
            raise ValueError("Last working date cannot be before the resignation effective date")
        return self


class LifecycleDecision(BaseModel):
    status: Literal["Approved", "Rejected"]


class ClearanceUpdate(BaseModel):
    status: Literal["Completed", "Pending"]


class ClearanceItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    owner: str
    status: str
    completed_by: str | None
    completed_at: datetime | None


class LifecycleCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int
    case_type: str
    status: str
    effective_date: date
    reason: str
    changes: dict[str, Any]
    created_by: str
    created_at: datetime
    decided_at: datetime | None
    clearance: list[ClearanceItemOut] = []


class EmployeeLifecycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: int
    employee_name: str
    department: str
    location: str
    role: str
    manager: str
    start_date: date | None
    probation_due_date: date | None
    probation_status: str
    cases: list[LifecycleCaseOut]
    status_history: list[EmployeeStatusEventOut] = []
