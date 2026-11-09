from datetime import date

from pydantic import BaseModel, Field


class ActivityCreate(BaseModel):
    activity_type: str = Field(default="note", min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    activity_date: date = Field(default_factory=date.today)
    metadata: dict | None = None


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    priority: str = Field(default="Medium", max_length=20)
    due_date: date | None = None
    progress_percentage: float = Field(default=0, ge=0, le=100)
    progress_notes: str | None = None


class TaskUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    progress_percentage: float | None = Field(default=None, ge=0, le=100)
    progress_notes: str | None = None
    comment: str | None = Field(default=None, min_length=1, max_length=10000)


class TaskCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=10000)


class KRAProgressUpdate(BaseModel):
    progress_percentage: float = Field(ge=0, le=100)
    progress_notes: str | None = None
    status: str | None = Field(default=None, max_length=30)


class KRACreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    weight: float = Field(default=1, gt=0)
    period_start: date
    period_end: date


class KPIUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = None
    target_value: float | None = Field(default=None, ge=0)
    actual_value: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=40)
    weight: float | None = Field(default=None, gt=0)
    score: float | None = Field(default=None, ge=0, le=100)
    status: str | None = Field(default=None, max_length=30)
    actual_notes: str | None = Field(default=None, max_length=2000)


class KPICreate(KPIUpdate):
    name: str = Field(min_length=1, max_length=200)
    target_value: float = Field(default=0, ge=0)


class ReviewCreate(BaseModel):
    review_period: str = Field(min_length=1, max_length=40)
    review_type: str = Field(default="Manager", max_length=40)
    overall_score: float | None = Field(default=None, ge=0, le=100)
    strengths: str | None = None
    development_areas: str | None = None
    comments: str | None = None
    status: str = Field(default="Draft", max_length=30)


class FeedbackCreate(BaseModel):
    relationship: str = Field(default="Peer", max_length=40)
    score: float | None = Field(default=None, ge=0, le=100)
    comments: str | None = None
    anonymous: bool = False


class KPIActualUpdate(BaseModel):
    actual_value: float = Field(ge=0)
    notes: str | None = Field(default=None, max_length=2000)


class ProgressReportCreate(BaseModel):
    period_type: str = Field(default="Weekly", max_length=20)
    period_start: date
    period_end: date
    summary: str = Field(default="", max_length=10000)
    achievements: str | None = Field(default=None, max_length=10000)
    blockers: str | None = Field(default=None, max_length=10000)


class ProgressReportUpdate(BaseModel):
    period_type: str | None = Field(default=None, max_length=20)
    period_start: date | None = None
    period_end: date | None = None
    summary: str | None = Field(default=None, max_length=10000)
    achievements: str | None = Field(default=None, max_length=10000)
    blockers: str | None = Field(default=None, max_length=10000)


class ProgressReportReview(BaseModel):
    status: str = Field(default="Reviewed", max_length=20)
    review_feedback: str | None = Field(default=None, max_length=10000)
