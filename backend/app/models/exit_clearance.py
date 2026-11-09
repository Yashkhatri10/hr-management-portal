from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base


class ExitClearanceItem(Base):
    __tablename__ = "exit_clearance_items"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("employee_lifecycle_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    owner = Column(String(40), nullable=False)
    status = Column(String(20), nullable=False, default="Pending")
    completed_by = Column(String(255), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
