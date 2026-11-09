from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EmployeeLifecycleStatus = Literal["Active", "On Notice", "On Leave", "Pending", "Resigned", "Terminated", "Inactive"]


class EmployeeStatusUpdate(BaseModel):
    status: EmployeeLifecycleStatus
    effective_date: date
    reason: str = Field(min_length=3, max_length=2000)


class EmployeeStatusEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_status: str
    new_status: str
    effective_date: date
    reason: str
    changed_by: str
    created_at: datetime
