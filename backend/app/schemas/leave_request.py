from datetime import date

from pydantic import BaseModel, EmailStr, Field, model_validator


class LeaveRequestCreate(BaseModel):
    employee_name: str = Field(min_length=1, max_length=120)
    employee_email: EmailStr
    leave_type: str = Field(min_length=1, max_length=40)
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=2000)
    is_half_day: bool = False

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date")
        if self.is_half_day and self.start_date != self.end_date:
            raise ValueError("A half-day leave request must use the same start and end date")
        return self


class LeaveRequestOut(LeaveRequestCreate):
    id: int
    status: str
    paid_days: float = 0
    unpaid_days: float = 0


class LeaveRequestList(BaseModel):
    requests: list[LeaveRequestOut]
