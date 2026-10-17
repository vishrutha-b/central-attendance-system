"""Attendance Regularization schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.common import CAMSBaseModel

RegularizationStatus = Literal["pending", "approved", "rejected"]
RegularizationReason = Literal[
    "forgot_punch",
    "onsite_visit",
    "biometric_error",
    "technical_glitch",
    "emergency",
    "other",
]


class RegularizationCreate(CAMSBaseModel):
    employee_id: Annotated[str, Field(min_length=1, max_length=50)]
    date: date
    requested_entry_time: Annotated[str, Field(min_length=4, max_length=50)]
    requested_exit_time: Annotated[str, Field(min_length=4, max_length=50)]
    reason: RegularizationReason = "forgot_punch"
    notes: Annotated[str | None, Field(default=None, max_length=500)] = None

    @model_validator(mode="after")
    def normalize_fields(self) -> RegularizationCreate:
        self.employee_id = self.employee_id.strip().upper()
        self.requested_entry_time = self.requested_entry_time.strip()
        self.requested_exit_time = self.requested_exit_time.strip()
        return self


class RegularizationDecision(CAMSBaseModel):
    action: Literal["approved", "rejected"]
    reviewer_notes: Annotated[str | None, Field(default=None, max_length=500)] = None


class RegularizationResponse(CAMSBaseModel):
    request_id: str
    employee_id: str
    date: date
    requested_entry_time: str
    requested_exit_time: str
    reason: str
    notes: str | None = None
    status: RegularizationStatus
    reviewed_by: str | None = None
    reviewer_notes: str | None = None
    created_at: datetime
    updated_at: datetime
