from sqlalchemy import Boolean, Column, Date, Integer, Numeric, String, Text

from app.database import Base


class PaidLeavePolicy(Base):
    __tablename__ = "paid_leave_policies"

    id = Column(Integer, primary_key=True)
    effective_from = Column(Date, nullable=False, unique=True, index=True)
    probation_days = Column(Integer, nullable=False, default=180)
    probation_monthly_days = Column(Numeric(6, 2), nullable=False, default=1)
    regular_monthly_days = Column(Numeric(6, 2), nullable=False, default=2.5)
    paid_leave_types_json = Column(Text, nullable=False, default='["Annual", "Paid Leave"]')
    allow_negative_balance = Column(Boolean, nullable=False, default=False)
    updated_by = Column(String(255), nullable=False)
