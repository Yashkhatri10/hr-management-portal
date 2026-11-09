from datetime import date

from pydantic import BaseModel, Field


class OnboardingRecordCreate(BaseModel):
    onboarding_start_date: date | None = None
    deadline: date | None = None
    coordinator_email: str | None = None
    notes: str | None = Field(default=None, max_length=4000)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)


class TemplateItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    owner: str = Field(default="HR", max_length=40)
    mandatory: bool = True
    due_days: int | None = Field(default=None, ge=0, le=3650)
    sort_order: int = Field(default=0, ge=0)


class OnboardingTaskEdit(BaseModel):
    status: str
    comments: str | None = Field(default=None, max_length=2000)


class DocumentDecision(BaseModel):
    status: str
    rejection_reason: str | None = Field(default=None, max_length=2000)
