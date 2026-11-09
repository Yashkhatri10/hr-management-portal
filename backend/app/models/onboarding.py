from datetime import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func

from app.database import Base


class OnboardingRecord(Base):
    __tablename__ = "onboarding_records"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="In Progress")
    onboarding_start_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    coordinator_email = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class OnboardingTemplate(Base):
    __tablename__ = "onboarding_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(160), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class OnboardingTemplateItem(Base):
    __tablename__ = "onboarding_template_items"
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("onboarding_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    description = Column(String(500), nullable=False, default="")
    owner = Column(String(40), nullable=False, default="HR")
    mandatory = Column(Boolean, nullable=False, default=True)
    due_days = Column(Integer, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)


class OnboardingDocument(Base):
    __tablename__ = "onboarding_documents"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    document_type = Column(String(80), nullable=False)
    filename = Column(String(255), nullable=False)
    storage_name = Column(String(255), nullable=False, unique=True)
    status = Column(String(30), nullable=False, default="Uploaded")
    rejection_reason = Column(Text, nullable=True)
    uploaded_by = Column(String, nullable=False)
    verified_by = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)


class OnboardingNotification(Base):
    __tablename__ = "onboarding_notifications"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, index=True)
    recipient_email = Column(String, nullable=False, index=True)
    message = Column(String(500), nullable=False)
    link = Column(String(255), nullable=True)
    event_key = Column(String(180), nullable=False, unique=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
