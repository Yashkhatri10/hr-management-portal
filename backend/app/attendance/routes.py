from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_hr_manager
from app.config import settings
from app.database import get_db
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.face_template import FaceTemplate
from app.schemas.attendance import AttendanceList, AttendanceRecordCreate, AttendanceRecordOut
from app.services.face_recognition import extract_embedding, serialize_embedding, verify_embedding
from app.services.geofence import validate_attendance_location, validate_gps_reading
from app.services.notifications import add_notifications, users_for_employee_manager, users_for_hr

router = APIRouter(prefix="/attendance", tags=["attendance"])
APP_TIMEZONE = ZoneInfo(settings.app_timezone)


def _get_today_string():
    return datetime.now(APP_TIMEZONE).strftime("%Y-%m-%d")


def _get_now_time_string():
    return datetime.now(APP_TIMEZONE).strftime("%H:%M")


def check_in_employee(employee_name: str, employee_email: str, payload: AttendanceRecordCreate, db: Session, face_image: bytes | None = None):
    distance = validate_attendance_location(payload.latitude, payload.longitude, payload.accuracy_meters)
    _verify_employee_face(employee_email, face_image, db)
    today = _get_today_string()
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_email == employee_email,
        AttendanceRecord.date == today,
    ).first()

    if record is None:
        check_in = _get_now_time_string()
        record = AttendanceRecord(
            employee_name=employee_name,
            employee_email=employee_email,
            date=today,
            check_in=check_in,
            status="Late" if check_in > "09:30" else "Present",
            notes="Checked in",
            check_in_latitude=payload.latitude, check_in_longitude=payload.longitude,
            check_in_accuracy_meters=payload.accuracy_meters, check_in_distance_meters=distance,
        )
        db.add(record)
    else:
        if record.check_in:
            raise HTTPException(status_code=409, detail="You have already checked in today")
        record.check_in = _get_now_time_string()
        record.status = "Late" if record.check_in > "09:30" else "Present"
        record.notes = (record.notes or "") + " | Checked in"
        record.check_in_latitude = payload.latitude
        record.check_in_longitude = payload.longitude
        record.check_in_accuracy_meters = payload.accuracy_meters
        record.check_in_distance_meters = distance

    db.flush()
    if record.status == "Late":
        employee = db.query(Employee).filter(Employee.email.ilike(employee_email)).first()
        add_notifications(
            db, [*(users_for_employee_manager(db, employee) if employee else []), *users_for_hr(db)],
            notification_type="attendance_exception", title="Late attendance",
            message=f"{employee_name} checked in late on {today}.", module="attendance",
            related_record_id=record.id, action_link="/attendance",
            event_key=f"attendance:late:{record.id}:{today}",
        )
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "employee_name": record.employee_name,
        "employee_email": record.employee_email,
        "date": record.date,
        "check_in": record.check_in,
        "check_out": record.check_out,
        "status": record.status,
        "notes": record.notes,
        "check_in_latitude": record.check_in_latitude, "check_in_longitude": record.check_in_longitude,
        "check_in_accuracy_meters": record.check_in_accuracy_meters, "check_in_distance_meters": record.check_in_distance_meters,
    }


def check_out_employee(employee_name: str, employee_email: str, payload: AttendanceRecordCreate, db: Session, face_image: bytes | None = None, reason: str = "MANUAL"):
    distance = validate_attendance_location(payload.latitude, payload.longitude, payload.accuracy_meters)
    _verify_employee_face(employee_email, face_image, db)
    today = _get_today_string()
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_email == employee_email,
        AttendanceRecord.date == today,
    ).first()

    if record is None:
        raise HTTPException(status_code=409, detail="Check in before checking out")
    else:
        if record.check_out:
            raise HTTPException(status_code=409, detail="You have already checked out today")
        if not record.check_in:
            raise HTTPException(status_code=409, detail="Check in before checking out")
        record.check_out = _get_now_time_string()
        record.status = "Present"
        record.notes = (record.notes or "") + " | Checked out"
        record.check_out_latitude = payload.latitude
        record.check_out_longitude = payload.longitude
        record.check_out_accuracy_meters = payload.accuracy_meters
        record.check_out_distance_meters = distance
        record.checkout_reason = reason

    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "employee_name": record.employee_name,
        "employee_email": record.employee_email,
        "date": record.date,
        "check_in": record.check_in,
        "check_out": record.check_out,
        "status": record.status,
        "notes": record.notes,
        "check_in_latitude": record.check_in_latitude, "check_in_longitude": record.check_in_longitude,
        "check_in_accuracy_meters": record.check_in_accuracy_meters, "check_in_distance_meters": record.check_in_distance_meters,
        "check_out_latitude": record.check_out_latitude, "check_out_longitude": record.check_out_longitude,
        "check_out_accuracy_meters": record.check_out_accuracy_meters, "check_out_distance_meters": record.check_out_distance_meters,
    }


def _verify_employee_face(employee_email: str, face_image: bytes | None, db: Session) -> None:
    if not face_image:
        raise HTTPException(status_code=422, detail="A live face capture is required for attendance")
    template = (
        db.query(FaceTemplate)
        .join(Employee, Employee.id == FaceTemplate.employee_id)
        .filter(Employee.email == employee_email)
        .first()
    )
    if template is None:
        raise HTTPException(status_code=409, detail="Face enrollment is required before attendance")
    verify_embedding(face_image, template.embedding)


@router.get("", response_model=AttendanceList)
def get_attendance(db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = db.query(AttendanceRecord)
    if user.role != "HR Manager":
        query = query.filter(AttendanceRecord.employee_email == user.email)
    records = query.order_by(AttendanceRecord.date.desc()).all()

    present = sum(1 for r in records if r.status == "Present")
    late = sum(1 for r in records if r.status == "Late")
    absent = sum(1 for r in records if r.status == "Absent")
    total = max(len(records), 1)

    return {
        "records": [
            {
                "id": r.id,
                "employee_name": r.employee_name,
                "employee_email": r.employee_email,
                "date": r.date,
                "check_in": r.check_in,
                "check_out": r.check_out,
                "status": r.status,
                "notes": r.notes,
                "check_in_latitude": r.check_in_latitude, "check_in_longitude": r.check_in_longitude,
                "check_in_accuracy_meters": r.check_in_accuracy_meters, "check_in_distance_meters": r.check_in_distance_meters,
                "check_out_latitude": r.check_out_latitude, "check_out_longitude": r.check_out_longitude,
                "check_out_accuracy_meters": r.check_out_accuracy_meters, "check_out_distance_meters": r.check_out_distance_meters,
            }
            for r in records
        ],
        "summary": {
            "present": present,
            "late": late,
            "absent": absent,
            "attendanceRate": round(((present + late) / total) * 100, 1),
        },
    }


@router.post("/check-in", response_model=AttendanceRecordOut)
def api_check_in(payload: AttendanceRecordCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return check_in_employee(user.name, user.email, payload, db)


@router.post("/check-out", response_model=AttendanceRecordOut)
def api_check_out(payload: AttendanceRecordCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return check_out_employee(user.name, user.email, payload, db)


@router.post("/check-in-verified", response_model=AttendanceRecordOut)
async def api_check_in_verified(
    employee_name: str = Form(...), employee_email: str = Form(...), date: str = Form(...),
    latitude: float = Form(...), longitude: float = Form(...), accuracy_meters: float = Form(...),
    face_image: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user),
):
    if employee_email != user.email:
        raise HTTPException(status_code=403, detail="Attendance identity must match the signed-in employee")
    payload = AttendanceRecordCreate(
        employee_name=employee_name, employee_email=employee_email, date=date,
        latitude=latitude, longitude=longitude, accuracy_meters=accuracy_meters,
    )
    return check_in_employee(user.name, user.email, payload, db, await face_image.read())


@router.post("/check-out-verified", response_model=AttendanceRecordOut)
async def api_check_out_verified(
    employee_name: str = Form(...), employee_email: str = Form(...), date: str = Form(...),
    latitude: float = Form(...), longitude: float = Form(...), accuracy_meters: float = Form(...),
    face_image: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user),
):
    if employee_email != user.email:
        raise HTTPException(status_code=403, detail="Attendance identity must match the signed-in employee")
    payload = AttendanceRecordCreate(
        employee_name=employee_name, employee_email=employee_email, date=date,
        latitude=latitude, longitude=longitude, accuracy_meters=accuracy_meters,
    )
    return check_out_employee(user.name, user.email, payload, db, await face_image.read())


@router.post("/face-enrollment/{employee_id}")
async def enroll_face(
    employee_id: int, face_image: UploadFile = File(...),
    db: Session = Depends(get_db), hr=Depends(require_hr_manager),
):
    employee = db.query(Employee).filter(Employee.id == employee_id, Employee.is_active.is_(True)).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Active employee not found")
    embedding = extract_embedding(await face_image.read())
    template = db.query(FaceTemplate).filter(FaceTemplate.employee_id == employee_id).first()
    if template is None:
        template = FaceTemplate(
            employee_id=employee_id, embedding=serialize_embedding(embedding),
            model_name="insightface-buffalo_l", enrolled_by=hr.email,
        )
        db.add(template)
    else:
        template.embedding = serialize_embedding(embedding)
        template.model_name = "insightface-buffalo_l"
        template.enrolled_by = hr.email
    db.commit()
    return {"status": "enrolled", "employee_id": employee_id}


@router.delete("/face-enrollment/{employee_id}")
def remove_face_enrollment(employee_id: int, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    template = db.query(FaceTemplate).filter(FaceTemplate.employee_id == employee_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Face enrollment not found")
    db.delete(template)
    db.commit()
    return {"status": "removed", "employee_id": employee_id}


@router.post("/geofence-monitor")
def monitor_geofence(payload: AttendanceRecordCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    distance = validate_gps_reading(payload.latitude, payload.longitude, payload.accuracy_meters)
    today = _get_today_string()
    record = db.query(AttendanceRecord).filter(
        AttendanceRecord.employee_email == user.email,
        AttendanceRecord.date == today,
        AttendanceRecord.check_in.isnot(None),
        AttendanceRecord.check_out.is_(None),
    ).first()
    if record is None:
        return {"state": "inactive", "distance_meters": distance}
    now = datetime.now(APP_TIMEZONE)
    if distance <= settings.office_geofence_radius_meters:
        record.geofence_exit_confirmations = 0
        record.geofence_outside_since = None
        db.commit()
        return {"state": "inside", "distance_meters": distance}
    record.geofence_exit_confirmations = (record.geofence_exit_confirmations or 0) + 1
    if record.geofence_exit_confirmations < settings.geofence_exit_confirmations:
        db.commit()
        return {"state": "confirming_exit", "confirmations": record.geofence_exit_confirmations, "distance_meters": distance}
    if record.geofence_outside_since is None:
        record.geofence_outside_since = now
    grace_ends = record.geofence_outside_since + timedelta(seconds=settings.geofence_exit_grace_period_seconds)
    if not settings.auto_checkout_on_geofence_exit or now < grace_ends:
        db.commit()
        return {"state": "grace_period", "grace_ends_at": grace_ends.isoformat(), "distance_meters": distance}
    record.check_out = _get_now_time_string()
    record.checkout_reason = "GEOFENCE_EXIT"
    record.status = "Present"
    record.notes = (record.notes or "") + " | Automatic checkout after geofence exit"
    record.check_out_latitude = payload.latitude
    record.check_out_longitude = payload.longitude
    record.check_out_accuracy_meters = payload.accuracy_meters
    record.check_out_distance_meters = distance
    db.commit()
    return {"state": "auto_checked_out", "distance_meters": distance, "checkout_reason": record.checkout_reason}


@router.post("", response_model=AttendanceRecordOut)
def create_attendance_record(payload: AttendanceRecordCreate, db: Session = Depends(get_db), _hr=Depends(require_hr_manager)):
    record = AttendanceRecord(
        employee_name=payload.employee_name,
        employee_email=payload.employee_email,
        date=payload.date,
        check_in=payload.check_in,
        check_out=payload.check_out,
        status=payload.status,
        notes=payload.notes,
        check_in_latitude=payload.latitude, check_in_longitude=payload.longitude,
        check_in_accuracy_meters=payload.accuracy_meters,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "employee_name": record.employee_name,
        "employee_email": record.employee_email,
        "date": record.date,
        "check_in": record.check_in,
        "check_out": record.check_out,
        "status": record.status,
        "notes": record.notes,
        "check_in_latitude": record.check_in_latitude, "check_in_longitude": record.check_in_longitude,
        "check_in_accuracy_meters": record.check_in_accuracy_meters,
    }
