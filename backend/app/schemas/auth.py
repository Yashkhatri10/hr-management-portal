from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    employee_id: int | None = None


class LoginResponse(BaseModel):
    token: str
    user: UserOut
