from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class EmployeeStatusEvent(Base):
    __tablename__ = "employee_status_events"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(30), nullable=False)
    new_status = Column(String(30), nullable=False)
    effective_date = Column(Date, nullable=False)
    reason = Column(Text, nullable=False)
    changed_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
