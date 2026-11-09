from pydantic import BaseModel


class AttendanceRecordCreate(BaseModel):
    employee_name: str
    employee_email: str
    date: str
    check_in: str | None = None
    check_out: str | None = None
    status: str = "Present"
    notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = None


class AttendanceRecordOut(AttendanceRecordCreate):
    id: int
    check_in_latitude: float | None = None
    check_in_longitude: float | None = None
    check_in_accuracy_meters: float | None = None
    check_in_distance_meters: float | None = None
    check_out_latitude: float | None = None
    check_out_longitude: float | None = None
    check_out_accuracy_meters: float | None = None
    check_out_distance_meters: float | None = None


class AttendanceSummary(BaseModel):
    present: int
    late: int
    absent: int
    attendanceRate: float


class AttendanceList(BaseModel):
    records: list[AttendanceRecordOut]
    summary: AttendanceSummary
