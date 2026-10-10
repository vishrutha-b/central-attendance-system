"""Report request/response schemas."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import CAMSBaseModel

ReportPeriod = Literal["daily", "weekly", "monthly", "yearly", "custom"]


class ReportQueryParams(CAMSBaseModel):
    period: ReportPeriod
    date: date | None = None  # daily
    start_date: date | None = None  # weekly, custom
    end_date: date | None = None  # custom
    year: int | None = None  # monthly, yearly
    month: int | None = Field(default=None, ge=1, le=12)  # monthly
    department: str | None = None
    is_active: bool | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_period_params(self) -> ReportQueryParams:
        if self.period == "daily" and self.date is None:
            raise ValueError("date is required for daily period")
        if self.period == "weekly" and self.start_date is None:
            raise ValueError("start_date is required for weekly period")
        if self.period == "monthly" and (self.year is None or self.month is None):
            raise ValueError("year and month are required for monthly period")
        if self.period == "yearly" and self.year is None:
            raise ValueError("year is required for yearly period")
        if self.period == "custom":
            if self.start_date is None or self.end_date is None:
                raise ValueError("start_date and end_date are required for custom period")
            if self.end_date < self.start_date:
                raise ValueError("end_date must be >= start_date")
        return self


class ComplianceStatus(CAMSBaseModel):
    is_compliant: bool | None  # None = cannot evaluate (incomplete week)
    is_evaluable: bool  # False = incomplete or no data
    violation_reasons: list[str]
    days_attended: int
    total_hours: float
    avg_hours_per_day: float
    completed_sessions: int
    incomplete_sessions: int
    period_start: date
    period_end: date


class EmployeeAttendanceReport(CAMSBaseModel):
    employee_id: str
    name: str
    email: str
    department: str
    is_active: bool
    total_days_attended: int
    total_valid_hours: float
    avg_hours_per_attended_day: float
    completed_sessions: int
    incomplete_sessions: int
    invalid_sessions: int
    missing_dates: list[date]
    approved_leave_dates: list[date]
    holiday_dates: list[date]
    weekly_compliance: list[ComplianceStatus]
    has_no_attendance: bool


class CompanySummary(CAMSBaseModel):
    total_employees: int
    compliant_count: int
    non_compliant_count: int
    no_attendance_count: int
    incomplete_attendance_count: int
    pending_evaluation_count: int
    total_valid_hours: float
    avg_hours_per_employee: float
    period_start: date
    period_end: date
    timezone: str


class AttendanceReport(CAMSBaseModel):
    period: ReportPeriod
    period_start: date
    period_end: date
    timezone: str
    employees: list[EmployeeAttendanceReport]
    company_summary: CompanySummary
    page: int
    page_size: int
    total: int
    total_pages: int
