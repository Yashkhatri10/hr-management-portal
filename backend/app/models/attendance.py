from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.database import Base


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, index=True)
    employee_name = Column(String, nullable=False)
    employee_email = Column(String, nullable=False)
    date = Column(String, nullable=False)
    check_in = Column(String, nullable=True)
    check_out = Column(String, nullable=True)
    status = Column(String, nullable=False, default="Present")
    notes = Column(Text, nullable=True)
    check_in_latitude = Column(Float, nullable=True)
    check_in_longitude = Column(Float, nullable=True)
    check_in_accuracy_meters = Column(Float, nullable=True)
    check_in_distance_meters = Column(Float, nullable=True)
    check_out_latitude = Column(Float, nullable=True)
    check_out_longitude = Column(Float, nullable=True)
    check_out_accuracy_meters = Column(Float, nullable=True)
    check_out_distance_meters = Column(Float, nullable=True)
    geofence_exit_confirmations = Column(Integer, nullable=False, default=0)
    geofence_outside_since = Column(DateTime(timezone=True), nullable=True)
    checkout_reason = Column(String, nullable=True)
