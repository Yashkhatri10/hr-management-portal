from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text

from app.database import Base


class EmployeeActivity(Base):
    __tablename__ = "employee_activities"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_email = Column(String, nullable=False)
    activity_type = Column(String, nullable=False, default="note")
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    activity_date = Column(Date, nullable=False, default=date.today, index=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EmployeeTask(Base):
    __tablename__ = "employee_tasks"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assigned_by = Column(String, nullable=False)
    priority = Column(String, nullable=False, default="Medium")
    status = Column(String, nullable=False, default="Not Started")
    progress_percentage = Column(Float, nullable=False, default=0)
    progress_notes = Column(Text, nullable=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EmployeeTaskHistory(Base):
    """Append-only snapshots of task status and progress changes."""
    __tablename__ = "employee_task_history"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("employee_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_email = Column(String, nullable=False)
    status = Column(String, nullable=False)
    progress_percentage = Column(Float, nullable=False)
    progress_notes = Column(Text, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class EmployeeTaskComment(Base):
    """Append-only comments and updates attached to a task."""
    __tablename__ = "employee_task_comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("employee_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    author_email = Column(String, nullable=False)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class PerformanceKRA(Base):
    __tablename__ = "performance_kras"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    weight = Column(Float, nullable=False, default=1.0)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="Active")
    progress_percentage = Column(Float, nullable=False, default=0)
    progress_notes = Column(Text, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PerformanceKPI(Base):
    __tablename__ = "performance_kpis"

    id = Column(Integer, primary_key=True, index=True)
    kra_id = Column(Integer, ForeignKey("performance_kras.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_value = Column(Float, nullable=False, default=0)
    actual_value = Column(Float, nullable=True)
    unit = Column(String(40), nullable=True)
    weight = Column(Float, nullable=False, default=1.0)
    score = Column(Float, nullable=True)
    status = Column(String, nullable=False, default="Open")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PerformanceKPIHistory(Base):
    """Append-only snapshots of employee KPI actuals and calculated achievement."""
    __tablename__ = "performance_kpi_history"

    id = Column(Integer, primary_key=True, index=True)
    kpi_id = Column(Integer, ForeignKey("performance_kpis.id", ondelete="CASCADE"), nullable=False, index=True)
    actual_value = Column(Float, nullable=False)
    achievement_percentage = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    recorded_by = Column(String, nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class EmployeeProgressReport(Base):
    __tablename__ = "employee_progress_reports"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    period_type = Column(String(20), nullable=False)  # Weekly or Monthly
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    summary = Column(Text, nullable=False, default="")
    achievements = Column(Text, nullable=True)
    blockers = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="Draft")
    review_feedback = Column(Text, nullable=True)
    reviewer_email = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_email = Column(String, nullable=False)
    review_period = Column(String(40), nullable=False)
    review_type = Column(String(40), nullable=False, default="Manager")
    overall_score = Column(Float, nullable=True)
    strengths = Column(Text, nullable=True)
    development_areas = Column(Text, nullable=True)
    comments = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="Draft")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class PerformanceFeedback(Base):
    __tablename__ = "performance_feedback"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("performance_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_email = Column(String, nullable=False)
    relationship = Column(String(40), nullable=False, default="Peer")
    score = Column(Float, nullable=True)
    comments = Column(Text, nullable=True)
    anonymous = Column(Boolean, nullable=False, default=False)
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
