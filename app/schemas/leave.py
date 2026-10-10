"""Leave and Holiday schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import CAMSBaseModel

LeaveStatus = Literal["pending", "approved", "rejected", "cancelled"]
LeaveType = Literal["annual", "sick", "casual", "unpaid", "other"]


class LeaveRequestCreate(CAMSBaseModel):
    employee_id: Annotated[str, Field(min_length=1, max_length=50)]
    leave_type: LeaveType = "annual"
    start_date: date
    end_date: date
    reason: Annotated[str, Field(min_length=5, max_length=1000)]

    @model_validator(mode="after")
    def validate_dates(self) -> LeaveRequestCreate:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self

    @model_validator(mode="after")
    def normalize_employee_id(self) -> LeaveRequestCreate:
        self.employee_id = self.employee_id.strip().upper()
        return self


class LeaveRequestResponse(CAMSBaseModel):
    leave_id: str
    employee_id: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus
    reviewed_by: str | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class LeaveDecision(CAMSBaseModel):
    note: str | None = Field(default=None, max_length=500)


class HolidayCreate(CAMSBaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    date: date
    description: str | None = Field(default=None, max_length=500)


class HolidayResponse(CAMSBaseModel):
    holiday_id: str
    name: str
    date: date
    description: str | None
    created_at: datetime
