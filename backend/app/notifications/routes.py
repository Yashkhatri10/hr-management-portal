from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


def output(item: Notification) -> dict:
    return {
        "id": item.id,
        "notification_type": item.notification_type,
        "title": item.title,
        "message": item.message,
        "module": item.module,
        "related_record_id": item.related_record_id,
        "action_link": item.action_link,
        "is_read": item.is_read,
        "read_at": item.read_at,
        "created_at": item.created_at,
    }


@router.get("")
def list_notifications(
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.recipient_user_id == user.id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    rows = query.order_by(Notification.created_at.desc(), Notification.id.desc()).offset(offset).limit(limit).all()
    return {"notifications": [output(row) for row in rows], "offset": offset, "limit": limit}


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user=Depends(get_current_user)):
    count = db.query(func.count(Notification.id)).filter(
        Notification.recipient_user_id == user.id,
        Notification.is_read.is_(False),
    ).scalar()
    return {"count": int(count or 0)}


@router.get("/module-counts")
def module_counts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = db.query(Notification.module, func.count(Notification.id)).filter(
        Notification.recipient_user_id == user.id,
        Notification.is_read.is_(False),
    ).group_by(Notification.module).all()
    return {"counts": {module: count for module, count in rows}}


@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_user_id == user.id,
    ).first()
    if item is None:
        raise HTTPException(404, "Notification not found")
    if not item.is_read:
        item.is_read = True
        item.read_at = datetime.now(timezone.utc)
        db.commit()
    return output(item)


@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db), user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    updated = db.query(Notification).filter(
        Notification.recipient_user_id == user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True, "read_at": now}, synchronize_session=False)
    db.commit()
    return {"updated": updated}
