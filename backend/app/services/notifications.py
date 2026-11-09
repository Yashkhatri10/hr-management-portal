from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.notification import Notification
from app.models.user import User


def user_for_employee(db: Session, employee: Employee | None) -> User | None:
    if employee is None:
        return None
    if employee.id:
        user = db.query(User).filter(User.employee_id == employee.id, User.is_active.is_(True)).first()
        if user:
            return user
    return db.query(User).filter(User.email.ilike(employee.email), User.is_active.is_(True)).first()


def users_for_hr(db: Session) -> list[User]:
    return db.query(User).filter(User.role == "HR Manager", User.is_active.is_(True)).all()


def users_for_employee_manager(db: Session, employee: Employee) -> list[User]:
    manager = (employee.manager or "").strip()
    if not manager:
        return []
    manager_employee = db.query(Employee).filter(Employee.name.ilike(manager)).first()
    user = user_for_employee(db, manager_employee)
    return [user] if user else []


def add_notification(
    db: Session,
    recipient: User,
    *,
    notification_type: str,
    title: str,
    message: str,
    module: str,
    event_key: str,
    related_record_id: int | None = None,
    action_link: str | None = None,
) -> Notification | None:
    if db.query(Notification).filter(Notification.event_key == event_key).first():
        return None
    item = Notification(
        recipient_user_id=recipient.id,
        notification_type=notification_type,
        title=title,
        message=message,
        module=module,
        related_record_id=related_record_id,
        action_link=action_link,
        event_key=event_key,
    )
    db.add(item)
    return item


def add_notifications(
    db: Session,
    recipients: Iterable[User],
    **kwargs,
) -> None:
    base_event_key = kwargs.pop("event_key")
    seen: set[int] = set()
    for recipient in recipients:
        if recipient.id in seen:
            continue
        seen.add(recipient.id)
        add_notification(db, recipient, **kwargs, event_key=f"{base_event_key}:user:{recipient.id}")
