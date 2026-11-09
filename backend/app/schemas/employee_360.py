from datetime import date

from pydantic import BaseModel, Field, model_validator


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: str = Field(default="Not Started", max_length=30)
    progress_percentage: int = Field(default=0, ge=0, le=100)
    target_date: date | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: str | None = Field(default=None, max_length=30)
    progress_percentage: int | None = Field(default=None, ge=0, le=100)
    target_date: date | None = None


class DevelopmentPlanCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    actions: str | None = Field(default=None, max_length=10000)
    status: str = Field(default="Draft", max_length=30)
    target_date: date | None = None


class DevelopmentPlanUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    actions: str | None = Field(default=None, max_length=10000)
    status: str | None = Field(default=None, max_length=30)
    target_date: date | None = None


class DocumentCreate(BaseModel):
    document_type: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    reference_number: str | None = Field(default=None, max_length=120)
    issued_date: date | None = None
    expiry_date: date | None = None
    status: str = Field(default="Active", max_length=30)
    notes: str | None = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.issued_date and self.expiry_date and self.expiry_date < self.issued_date:
            raise ValueError("expiry_date cannot precede issued_date")
        return self


class DocumentUpdate(BaseModel):
    document_type: str | None = Field(default=None, min_length=1, max_length=60)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    reference_number: str | None = Field(default=None, max_length=120)
    issued_date: date | None = None
    expiry_date: date | None = None
    status: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=5000)
