from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PaidLeavePolicyUpdate(BaseModel):
    probation_days: int = Field(ge=0, le=730)
    probation_monthly_days: Decimal = Field(gt=0, le=Decimal("31"), decimal_places=2)
    regular_monthly_days: Decimal = Field(gt=0, le=Decimal("31"), decimal_places=2)
    paid_leave_types: list[str] = Field(min_length=1)
    allow_negative_balance: bool = False

    @field_validator("paid_leave_types")
    @classmethod
    def clean_leave_types(cls, value: list[str]) -> list[str]:
        cleaned = sorted({item.strip() for item in value if item.strip()})
        if not cleaned:
            raise ValueError("At least one paid leave type is required")
        return cleaned


class PaidLeaveAdjustment(BaseModel):
    amount: Decimal = Field(gt=Decimal("-1000000"), lt=Decimal("1000000"), decimal_places=2)
    effective_date: date
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("amount")
    @classmethod
    def validate_nonzero_amount(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Adjustment amount cannot be zero")
        return value
