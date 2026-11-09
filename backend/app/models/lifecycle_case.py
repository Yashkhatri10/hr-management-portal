from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class LifecycleCase(Base):
    __tablename__ = "employee_lifecycle_cases"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    case_type = Column(String(30), nullable=False)  # Transfer, Promotion, Resignation
    status = Column(String(20), nullable=False, default="Pending")
    effective_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    changes_json = Column(Text, nullable=False, default="{}")
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    decided_at = Column(DateTime(timezone=True), nullable=True)
