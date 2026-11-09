from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, func

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(60), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    module = Column(String(40), nullable=False, index=True)
    related_record_id = Column(Integer, nullable=True)
    action_link = Column(String(255), nullable=True)
    event_key = Column(String(255), nullable=False, unique=True)
    is_read = Column(Boolean, nullable=False, default=False, server_default="0", index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_notifications_recipient_unread", "recipient_user_id", "is_read"),
    )
