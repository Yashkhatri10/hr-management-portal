from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Text

from app.database import Base


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String, nullable=False)
    employee_email = Column(String, nullable=False)
    leave_type = Column(String, nullable=False)
    start_date = Column(String, nullable=False)
    end_date = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="Pending")
    is_half_day = Column(Boolean, nullable=False, default=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    paid_days = Column(Numeric(8, 2), nullable=True)
    unpaid_days = Column(Numeric(8, 2), nullable=True)
