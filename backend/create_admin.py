from getpass import getpass

from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.employee import Employee
from app.models.user import User

password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def main() -> None:
    name = input("HR manager full name: ").strip()
    email = input("HR manager work email: ").strip().lower()
    password = getpass("Password (minimum 12 characters): ")
    confirm = getpass("Confirm password: ")

    if not name or not email or len(password) < 12 or password != confirm:
        raise SystemExit("Name/email are required; password must be at least 12 characters and match confirmation.")

    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("An account with that email already exists.")
        user = User(name=name, email=email, password=password_context.hash(password), role="HR Manager", is_active=True)
        db.add(user)
        db.flush()
        if not db.query(Employee).filter(Employee.email == email).first():
            db.add(Employee(
                name=name,
                email=email,
                role="HR Manager",
                department="People Operations",
                location="India",
                status="Active",
                manager=name,
            ))
        db.commit()
        print(f"HR Manager account created for {email}.")
    except IntegrityError as exc:
        db.rollback()
        raise SystemExit("Could not create the account because the email already exists.") from exc
    finally:
        db.close()


if __name__ == "__main__":
    main()
