from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func

from app.database import Base


class PaidLeaveLedgerEntry(Base):
    __tablename__ = "paid_leave_ledger"
    __table_args__ = (UniqueConstraint("source_key", name="uq_paid_leave_ledger_source_key"),)

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    leave_request_id = Column(Integer, ForeignKey("leave_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    entry_type = Column(String(20), nullable=False)  # CREDIT, DEBIT, REVERSAL, ADJUSTMENT
    amount = Column(Numeric(8, 2), nullable=False)  # signed: credits positive, usage negative
    effective_date = Column(Date, nullable=False, index=True)
    period_key = Column(String(7), nullable=True, index=True)
    source_key = Column(String(160), nullable=False)
    note = Column(Text, nullable=False)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
