from sqlalchemy import Column, Date, ForeignKey, Integer, String

from app.database import Base


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    start_date = Column(Date, nullable=False)
    employment_end_date = Column(Date, nullable=True)
    employment_type = Column(String(40), nullable=False, default="Full-time")
    emergency_contact_name = Column(String(120), nullable=True)
    emergency_contact_relationship = Column(String(80), nullable=True)
    emergency_contact_phone = Column(String(30), nullable=True)
