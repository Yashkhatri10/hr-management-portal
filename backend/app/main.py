from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.attendance.routes import router as attendance_router
from app.auth.routes import router as auth_router
from app.config import settings
from app.database import Base, engine, ensure_runtime_schema
from app.dashboard.routes import router as dashboard_router
from app.employees.routes import router as employees_router
from app.employees.lifecycle_routes import router as lifecycle_router
from app.leave.routes import router as leave_router
from app.paid_leave.routes import router as paid_leave_router
from app.reports.routes import router as reports_router
from app.models.attendance import AttendanceRecord  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.employee_profile import EmployeeProfile  # noqa: F401
from app.models.employee_status_event import EmployeeStatusEvent  # noqa: F401
from app.models.employee_status_event import EmployeeStatusEvent  # noqa: F401
from app.models.exit_clearance import ExitClearanceItem  # noqa: F401
from app.models.lifecycle_case import LifecycleCase  # noqa: F401
from app.models.leave_request import LeaveRequest  # noqa: F401
from app.models.onboarding_task import OnboardingTask  # noqa: F401
from app.models.onboarding import OnboardingDocument, OnboardingNotification, OnboardingRecord, OnboardingTemplate, OnboardingTemplateItem  # noqa: F401
from app.models.paid_leave_ledger import PaidLeaveLedgerEntry  # noqa: F401
from app.models.paid_leave_policy import PaidLeavePolicy  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.face_template import FaceTemplate  # noqa: F401
from app.models.performance import EmployeeActivity, EmployeeTask, EmployeeTaskComment, EmployeeTaskHistory, EmployeeProgressReport, PerformanceFeedback, PerformanceKPI, PerformanceKPIHistory, PerformanceKRA, PerformanceReview  # noqa: F401
from app.models.employee_360 import EmployeeDocument, EmployeeGoal, DevelopmentPlan  # noqa: F401
from app.services.seed import seed_data
from app.performance.routes import router as performance_router
from app.onboarding.routes import router as onboarding_router
from app.notifications.routes import router as notifications_router

if settings.app_env.lower() != "production":
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
if settings.app_env.lower() != "production" and settings.seed_demo_data:
    seed_data()

app = FastAPI(
    title="HR Management Portal",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(employees_router)
app.include_router(lifecycle_router)
app.include_router(leave_router)
app.include_router(paid_leave_router)
app.include_router(reports_router)
app.include_router(attendance_router)
app.include_router(performance_router)
app.include_router(onboarding_router)
app.include_router(notifications_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
