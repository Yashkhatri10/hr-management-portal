from pydantic import BaseModel, EmailStr, Field

from app.schemas.onboarding import EmployeeProfileFields


class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr
    role: str
    department: str
    location: str
    status: str = "Active"
    manager: str


class EmployeeRegistration(EmployeeCreate, EmployeeProfileFields):
    password: str = Field(min_length=12)


class EmployeeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    role: str | None = Field(default=None, min_length=1, max_length=120)
    department: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, min_length=1, max_length=120)
    status: str | None = None
    manager: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    start_date: str | None = None
    employment_type: str | None = Field(default=None, min_length=1, max_length=40)
    emergency_contact_name: str | None = Field(default=None, max_length=120)
    emergency_contact_relationship: str | None = Field(default=None, max_length=80)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)


class EmployeeOut(EmployeeCreate):
    id: int
    phone: str | None = None
    start_date: str | None = None


class EmployeeList(BaseModel):
    employees: list[EmployeeOut]
