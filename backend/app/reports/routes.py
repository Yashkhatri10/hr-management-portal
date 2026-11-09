import csv
import io
from datetime import date
from decimal import Decimal
from typing import Any
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.auth.dependencies import require_hr_manager
from app.database import get_db
from app.employees.lifecycle_routes import _case_out, _employee_or_404
from app.models.attendance import AttendanceRecord
from app.models.employee import Employee
from app.models.employee_profile import EmployeeProfile
from app.models.employee_status_event import EmployeeStatusEvent
from app.models.exit_clearance import ExitClearanceItem
from app.models.lifecycle_case import LifecycleCase
from app.models.leave_request import LeaveRequest
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry
from app.models.performance import EmployeeTask, PerformanceKPI, PerformanceKRA, PerformanceReview
from app.models.employee_360 import EmployeeGoal, DevelopmentPlan, EmployeeDocument
from app.paid_leave.routes import resolve_period
from app.services.paid_leave import ensure_ledger_current, summarize_employee, today_local

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_hr_manager)])
REPORT_TYPES = {"lifecycle", "employees", "attendance", "paid-leave", "leave", "employee-360"}
FORMATS = {"csv", "xlsx", "pdf"}


def _safe_value(value: Any) -> Any:
    if isinstance(value, (date, Decimal)):
        return str(value)
    if value is None:
        return ""
    return value


def _build_report(
    report_type: str,
    db: Session,
    employee_id: int | None,
    search: str,
    department: str,
    status: str,
    from_date: date | None,
    to_date: date | None,
    period_type: str,
    period: str | None,
) -> tuple[str, list[str], list[list[Any]]]:
    if report_type == "employee-360":
        query = db.query(Employee)
        if employee_id is not None:
            query = query.filter(Employee.id == employee_id)
        if department:
            query = query.filter(Employee.department == department)
        if status:
            query = query.filter(Employee.status == status)
        employees = query.order_by(Employee.name).all()
        if search:
            term = search.casefold()
            employees = [e for e in employees if term in e.name.casefold() or term in e.email.casefold() or term in str(e.id)]
        headers = ["Employee ID", "Employee", "Email", "Department", "Designation", "Status", "Goals", "Development Plans", "Documents", "Tasks", "Completed Tasks", "KRAs", "KPIs", "Average KPI Score", "Reviews", "Average Review Score", "Attendance Rate", "Approved Leave Days"]
        rows = []
        for employee in employees:
            tasks = db.query(EmployeeTask).filter_by(employee_id=employee.id).all()
            kras = db.query(PerformanceKRA).filter_by(employee_id=employee.id).all()
            kpis = db.query(PerformanceKPI).filter(PerformanceKPI.kra_id.in_([kra.id for kra in kras])).all() if kras else []
            reviews = db.query(PerformanceReview).filter_by(employee_id=employee.id).all()
            attendance = db.query(AttendanceRecord).filter_by(employee_email=employee.email).all()
            leaves = db.query(LeaveRequest).filter_by(employee_email=employee.email, status="Approved").all()
            present = sum(item.status in {"Present", "Late"} for item in attendance)
            scores = [item.score for item in kpis if item.score is not None]
            review_scores = [item.overall_score for item in reviews if item.overall_score is not None]
            rows.append([
                employee.id, employee.name, employee.email, employee.department, employee.role, employee.status,
                db.query(EmployeeGoal).filter_by(employee_id=employee.id).count(),
                db.query(DevelopmentPlan).filter_by(employee_id=employee.id).count(),
                db.query(EmployeeDocument).filter_by(employee_id=employee.id).count(),
                len(tasks), sum(task.status == "Completed" for task in tasks), len(kras), len(kpis),
                round(sum(scores) / len(scores), 2) if scores else None, len(reviews),
                round(sum(review_scores) / len(review_scores), 2) if review_scores else None,
                round(present / len(attendance) * 100, 2) if attendance else 0,
                sum(float(item.paid_days or 0) for item in leaves),
            ])
        return "Employee 360 Summary", headers, rows

    if report_type == "employees":
        query = db.query(Employee)
        if department:
            query = query.filter(Employee.department == department)
        if status:
            query = query.filter(Employee.status == status)
        employees = query.order_by(Employee.name).all()
        profiles = {p.employee_id: p for p in db.query(EmployeeProfile).all()}
        if search:
            term = search.casefold()
            employees = [e for e in employees if term in e.name.casefold() or term in e.email.casefold() or term in str(e.id)]
        headers = ["Employee ID", "Name", "Email", "Designation", "Department", "Location", "Manager", "Status", "Joining Date", "Employment Type", "Phone"]
        rows = [[e.id, e.name, e.email, e.role, e.department, e.location, e.manager, e.status, profiles[e.id].start_date if e.id in profiles else None, profiles[e.id].employment_type if e.id in profiles else None, profiles[e.id].phone if e.id in profiles else None] for e in employees]
        return "Employee Directory", headers, rows

    if report_type == "attendance":
        query = db.query(AttendanceRecord)
        if employee_id is not None:
            employee = _employee_or_404(db, employee_id)
            query = query.filter(AttendanceRecord.employee_email == employee.email)
        if from_date:
            query = query.filter(AttendanceRecord.date >= from_date.isoformat())
        if to_date:
            query = query.filter(AttendanceRecord.date <= to_date.isoformat())
        if status:
            query = query.filter(AttendanceRecord.status == status)
        records = query.order_by(AttendanceRecord.date, AttendanceRecord.employee_name).all()
        if search:
            records = [r for r in records if search.casefold() in r.employee_name.casefold() or search.casefold() in r.employee_email.casefold()]
        headers = ["Employee", "Email", "Date", "Check In", "Check Out", "Status", "Notes"]
        rows = [[r.employee_name, r.employee_email, r.date, r.check_in, r.check_out, r.status, r.notes] for r in records]
        return "Attendance Report", headers, rows

    if report_type == "leave":
        query = db.query(LeaveRequest)
        if employee_id is not None:
            employee = _employee_or_404(db, employee_id)
            query = query.filter(LeaveRequest.employee_email == employee.email)
        if from_date:
            query = query.filter(LeaveRequest.start_date >= from_date.isoformat())
        if to_date:
            query = query.filter(LeaveRequest.end_date <= to_date.isoformat())
        if status:
            query = query.filter(LeaveRequest.status == status)
        requests = query.order_by(LeaveRequest.start_date, LeaveRequest.employee_name).all()
        if search:
            requests = [r for r in requests if search.casefold() in r.employee_name.casefold() or search.casefold() in r.employee_email.casefold()]
        headers = ["Request ID", "Employee", "Email", "Leave Type", "Start Date", "End Date", "Days", "Half Day", "Status", "Reason"]
        from app.services.paid_leave import business_leave_days
        rows = [[r.id, r.employee_name, r.employee_email, r.leave_type, r.start_date, r.end_date, business_leave_days(r), r.is_half_day, r.status, r.reason] for r in requests]
        return "Leave Requests Report", headers, rows

    if report_type == "paid-leave":
        start, end, label = resolve_period(period_type, period)
        as_of = min(end, today_local())
        ensure_ledger_current(db, as_of)
        query = db.query(Employee).order_by(Employee.name)
        if employee_id is not None:
            query = query.filter(Employee.id == employee_id)
        employees = query.all()
        rows_data = [summarize_employee(db, e, as_of, start) for e in employees]
        if search:
            term = search.casefold()
            rows_data = [r for r in rows_data if term in r["employee_name"].casefold() or term in r["email"].casefold() or term in str(r["employee_id"])]
        if department:
            rows_data = [r for r in rows_data if r["department"].casefold() == department.casefold()]
        if status:
            rows_data = [r for r in rows_data if r["employee_status"].casefold() == status.casefold()]
        headers = ["Employee ID", "Employee", "Email", "Department", "Designation", "Date Joined", "Probation/Regular", "Employee Status", "Monthly Entitlement", "Current Month Credit", "Opening Balance", "Total Credited", "Adjustments", "Paid Leave Used", "Unpaid Leave Used (Period)", "Remaining", "Pending Requests", "Utilization %"]
        rows = [[r["employee_id"], r["employee_name"], r["email"], r["department"], r["designation"], r["date_of_joining"], r["employment_status"], r["employee_status"], r["monthly_entitlement"], r["current_month_credit"], r["opening_balance"], r["total_credited"], r["manual_adjustments"], r["total_taken"], r["period_unpaid"], r["remaining_balance"], r["pending_requests"], r["utilization_percent"]] for r in rows_data]
        return f"Paid Leave Report — {label}", headers, rows

    if report_type == "lifecycle":
        query = db.query(Employee)
        if employee_id is not None:
            query = query.filter(Employee.id == employee_id)
        if department:
            query = query.filter(Employee.department == department)
        if status:
            query = query.filter(Employee.status == status)
        employees = query.order_by(Employee.name).all()
        if search:
            term = search.casefold()
            employees = [e for e in employees if term in e.name.casefold() or term in e.email.casefold() or term in str(e.id)]
        profiles = {p.employee_id: p for p in db.query(EmployeeProfile).all()}
        headers = ["Employee ID", "Employee", "Email", "Current Status", "Department", "Designation", "Manager", "Location", "Joining Date", "Event Type", "Event Status", "Effective Date", "Reason", "Changes", "Created By", "Created At", "Decided At"]
        rows: list[list[Any]] = []
        for employee in employees:
            profile = profiles.get(employee.id)
            cases = db.query(LifecycleCase).filter(LifecycleCase.employee_id == employee.id).order_by(LifecycleCase.created_at).all()
            events = db.query(EmployeeStatusEvent).filter(EmployeeStatusEvent.employee_id == employee.id).order_by(EmployeeStatusEvent.created_at).all()
            for case in cases:
                changes = _case_out(case, db)["changes"]
                rows.append([employee.id, employee.name, employee.email, employee.status, employee.department, employee.role, employee.manager, employee.location, profile.start_date if profile else None, case.case_type, case.status, case.effective_date, case.reason, "; ".join(f"{key}: {value}" for key, value in changes.items() if value is not None), case.created_by, case.created_at, case.decided_at])
            for event in events:
                rows.append([employee.id, employee.name, employee.email, employee.status, employee.department, employee.role, employee.manager, employee.location, profile.start_date if profile else None, "Status Change", f"{event.previous_status} → {event.new_status}", event.effective_date, event.reason, f"{event.previous_status} → {event.new_status}", event.changed_by, event.created_at, None])
            if not cases and not events:
                rows.append([employee.id, employee.name, employee.email, employee.status, employee.department, employee.role, employee.manager, employee.location, profile.start_date if profile else None, "Current state", "No lifecycle events", None, "", "", "", None, None])
        return "Employee Lifecycle Report", headers, rows

    raise HTTPException(status_code=404, detail="Unknown report type")


def _csv_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_value(value) for value in row])
    return output.getvalue().encode("utf-8-sig")


def _xlsx_bytes(title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="183454")
    for row in rows:
        sheet.append([_safe_value(value) for value in row])
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        letter = column[0].column_letter
        width = min(max(max((len(str(cell.value or "")) for cell in column), default=10) + 2, 12), 42)
        sheet.column_dimensions[letter].width = width
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _pdf_bytes(title: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#183454"))
    cell_style = ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=6.5, leading=8, wordWrap="CJK")
    data = [[Paragraph(escape(str(value)), cell_style) for value in headers]]
    for row in rows:
        data.append([Paragraph(escape(str(_safe_value(value))), cell_style) for value in row])
    usable_width = landscape(letter)[0] - 48
    widths = [usable_width / len(headers)] * len(headers)
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#183454")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C7D2E0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    document.build([Paragraph(title, title_style), Spacer(1, 10), table])
    return output.getvalue()


@router.get("/{report_type}/{file_format}")
def download_report(
    report_type: str,
    file_format: str,
    employee_id: int | None = None,
    search: str = "",
    department: str = "",
    status: str = "",
    from_date: date | None = None,
    to_date: date | None = None,
    period_type: str = Query(default="month"),
    period: str | None = None,
    db: Session = Depends(get_db),
    _hr=Depends(require_hr_manager),
):
    if report_type not in REPORT_TYPES:
        raise HTTPException(status_code=404, detail=f"Unsupported report type: {report_type}")
    if file_format not in FORMATS:
        raise HTTPException(status_code=422, detail="File format must be csv, xlsx, or pdf")
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="from_date cannot be later than to_date")
    title, headers, rows = _build_report(report_type, db, employee_id, search, department, status, from_date, to_date, period_type, period)
    if file_format == "csv":
        content, media_type, extension = _csv_bytes(headers, rows), "text/csv; charset=utf-8", "csv"
    elif file_format == "xlsx":
        content, media_type, extension = _xlsx_bytes(title, headers, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    else:
        content, media_type, extension = _pdf_bytes(title, headers, rows), "application/pdf", "pdf"
    filename = f"{report_type}-report-{date.today().isoformat()}.{extension}"
    return StreamingResponse(io.BytesIO(content), media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store", "X-Report-Rows": str(len(rows))})
