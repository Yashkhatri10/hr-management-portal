from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class OnboardingTask(Base):
    __tablename__ = "onboarding_tasks"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(String(500), nullable=False)
    owner = Column(String(40), nullable=False, default="HR")
    status = Column(String(20), nullable=False, default="Not started")
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    mandatory = Column(Boolean, nullable=False, default=True)
    comments = Column(Text, nullable=True)
    updated_by = Column(String(255), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
