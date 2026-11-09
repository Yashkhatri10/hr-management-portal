from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.models.employee import Employee

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in required")
    claims = decode_access_token(credentials.credentials)
    user = db.query(User).filter(User.id == claims["sub"], User.is_active.is_(True)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is inactive or no longer exists")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this action")
        return user
    return dependency


require_hr_manager = require_roles("HR Manager")


def employee_for_user(db: Session, user: User) -> Employee | None:
    """Resolve the authenticated account to its employee record.

    The explicit mapping is preferred; email remains a backwards-compatible
    fallback for databases created before the mapping column existed.
    """
    if user.employee_id is not None:
        return db.query(Employee).filter(Employee.id == user.employee_id).first()
    return db.query(Employee).filter(Employee.email.ilike(user.email)).first()
