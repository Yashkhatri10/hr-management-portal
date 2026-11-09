from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.security import create_access_token
from app.models.user import User
from app.models.employee import Employee
from app.schemas.auth import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower(), User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    password_matches = (
        pwd_context.verify(payload.password, user.password)
        if user.password.startswith("$argon2")
        else user.password == payload.password
    )
    if not password_matches:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.password.startswith("$argon2"):
        user.password = pwd_context.hash(payload.password)
        db.commit()

    return LoginResponse(
        token=create_access_token(user.id, user.role, user.email),
        user={
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "employee_id": user.employee_id or db.query(Employee.id).filter(Employee.email.ilike(user.email)).scalar(),
        },
    )
