from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class EmployeeGoal(Base):
    __tablename__ = "employee_goals"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="Not Started")
    progress_percentage = Column(Integer, nullable=False, default=0)
    target_date = Column(Date, nullable=True)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DevelopmentPlan(Base):
    __tablename__ = "development_plans"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    actions = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="Draft")
    target_date = Column(Date, nullable=True)
    created_by = Column(String, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EmployeeDocument(Base):
    """Metadata only. File contents and sensitive document bytes are never stored."""

    __tablename__ = "employee_documents"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    document_type = Column(String(60), nullable=False)
    title = Column(String(200), nullable=False)
    issuer = Column(String(200), nullable=True)
    reference_number = Column(String(120), nullable=True)
    issued_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(String(30), nullable=False, default="Active")
    notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
