"""Attendance session request/response schemas."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from dateutil import parser
from pydantic import Field, field_validator, model_validator

from app.schemas.common import CAMSBaseModel

AttendanceStatus = Literal["complete", "incomplete", "invalid"]


def parse_flexible_datetime(
    v: Any,
    default_to_now: bool = True,
    base_date: date | None = None,
    company_tz_name: str = "Asia/Kolkata",
) -> datetime | None:
    """Parse a flexible datetime or time string into a timezone-aware UTC datetime.

    Accepts:
    - None / '' / 'string': defaults to current time if default_to_now is True, else None.
    - 'now' / 'current': current time in UTC.
    - Time-only strings ('09:30', '18:00', '9:30 AM'): resolved relative to base_date (today).
    - Date-time strings ('2026-10-09 09:30', '2026-10-09T09:30:00Z').
    - datetime objects.
    """
    try:
        tz = ZoneInfo(company_tz_name)
    except Exception:
        tz = UTC

    now = datetime.now(tz=UTC)

    if v is None:
        return now if default_to_now else None

    if isinstance(v, str):
        v_str = v.strip()
        if v_str in ("", "string", "null", "None"):
            return now if default_to_now else None
        if v_str.lower() in ("now", "current"):
            return now

        today_local = datetime.now(tz=tz).date() if base_date is None else base_date
        base_dt = datetime(today_local.year, today_local.month, today_local.day, tzinfo=tz)

        try:
            parsed = parser.parse(v_str, default=base_dt)
        except Exception as exc:
            raise ValueError(
                f"Invalid time format: '{v}'. "
                "Use simple time (e.g. '09:30', '18:00') or ISO format."
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=tz)
        return parsed.astimezone(UTC)

    if isinstance(v, datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=tz)
        return v.astimezone(UTC)

    return None


class AttendanceEntryRequest(CAMSBaseModel):
    employee_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Employee identifier (e.g. 'EMP-001')",
            examples=["EMP-001"],
        ),
    ]
    date: Annotated[
        date | str | None,
        Field(
            default=None,
            description="Date for this entry (YYYY-MM-DD). Defaults to today if omitted.",
            examples=["2026-10-05"],
        ),
    ] = None
    entry_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description=(
                "Entry time (e.g. '09:30' or ISO timestamp). "
                "Defaults to current time if omitted."
            ),
            examples=["09:30"],
        ),
    ] = None

    @field_validator("employee_id")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def resolve_entry_time(self) -> AttendanceEntryRequest:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Asia/Kolkata")
        # Resolve base date
        if self.date is None:
            base = datetime.now(tz=tz).date()
        elif isinstance(self.date, str):
            base = date.fromisoformat(self.date.strip())
        else:
            base = self.date
        # Re-parse entry_time using the resolved date as base
        self.entry_time = parse_flexible_datetime(
            self.entry_time, default_to_now=True, base_date=base
        )
        return self


class AttendanceExitRequest(CAMSBaseModel):
    employee_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Employee identifier (e.g. 'EMP-001')",
            examples=["EMP-001"],
        ),
    ]
    date: Annotated[
        date | str | None,
        Field(
            default=None,
            description="Date for this exit (YYYY-MM-DD). Defaults to today if omitted.",
            examples=["2026-10-05"],
        ),
    ] = None
    exit_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description=(
                "Exit time (e.g. '18:00' or ISO timestamp). "
                "Defaults to current time if omitted."
            ),
            examples=["18:00"],
        ),
    ] = None

    @field_validator("employee_id")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def resolve_exit_time(self) -> AttendanceExitRequest:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("Asia/Kolkata")
        if self.date is None:
            base = datetime.now(tz=tz).date()
        elif isinstance(self.date, str):
            base = date.fromisoformat(self.date.strip())
        else:
            base = self.date
        self.exit_time = parse_flexible_datetime(
            self.exit_time, default_to_now=True, base_date=base
        )
        return self


class AttendanceQuickRecordRequest(CAMSBaseModel):
    employee_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=50,
            description="Employee identifier (e.g. 'EMP-001')",
            examples=["EMP-001"],
        ),
    ]
    date: Annotated[
        date | str | None,
        Field(
            default=None,
            description="Attendance date (YYYY-MM-DD). Defaults to today if omitted.",
            examples=["2026-10-09"],
        ),
    ] = None
    entry_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description="Entry time (e.g. '09:00', '09:30', or full ISO). Defaults to 09:00 AM.",
            examples=["09:00"],
        ),
    ] = None
    exit_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description=(
                "Exit time (e.g. '18:00', '18:30', or full ISO). "
                "Defaults to 18:00 (6:00 PM)."
            ),
            examples=["18:00"],
        ),
    ] = None

    @field_validator("employee_id")
    @classmethod
    def normalize_id(cls, v: str) -> str:
        return v.strip().upper()


class AttendanceCorrection(CAMSBaseModel):
    entry_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description="New entry time (e.g. '09:30' or full timestamp).",
            examples=["09:30"],
        ),
    ] = None
    exit_time: Annotated[
        datetime | str | None,
        Field(
            default=None,
            description="New exit time (e.g. '18:00' or full timestamp).",
            examples=["18:00"],
        ),
    ] = None
    reason: Annotated[
        str,
        Field(
            default="Manual correction",
            min_length=1,
            max_length=500,
            description="Reason for correction.",
            examples=["Corrected entry time"],
        ),
    ] = "Manual correction"

    @field_validator("entry_time", mode="before")
    @classmethod
    def parse_entry_time(cls, v: Any) -> datetime | None:
        return parse_flexible_datetime(v, default_to_now=False)

    @field_validator("exit_time", mode="before")
    @classmethod
    def parse_exit_time(cls, v: Any) -> datetime | None:
        return parse_flexible_datetime(v, default_to_now=False)

    @model_validator(mode="after")
    def at_least_one_field(self) -> AttendanceCorrection:
        if self.entry_time is None and self.exit_time is None:
            raise ValueError("At least one of entry_time or exit_time must be provided")
        return self


class AttendanceSessionResponse(CAMSBaseModel):
    attendance_id: str
    employee_id: str
    date: date
    entry_time: datetime
    exit_time: datetime | None
    total_hours: float
    attendance_status: AttendanceStatus
    created_at: datetime
    updated_at: datetime
    policy_alert: str | None = None


class AttendanceHistoryParams(CAMSBaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    start_date: date | None = None
    end_date: date | None = None
