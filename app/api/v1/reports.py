"""Reports endpoint — single primary endpoint for all period types + CSV export."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_admin, get_report_service
from app.config import get_settings
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])

# Formula injection characters to sanitize for CSV safety
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value: str) -> str:
    """Prevent CSV formula injection by prefixing dangerous values."""
    if value and value[0] in _FORMULA_PREFIXES:
        return f"'{value}"
    return value


def _resolve_period_dates(
    period: str,
    date_param: date | None,
    start_date: date | None,
    end_date: date | None,
    year: int | None,
    month: int | None,
    settings: Any,
) -> tuple[date, date]:
    """Resolve period parameters to (start, end) date range."""
    from app.services.policy_service import get_week_start

    if period == "daily":
        if date_param is None:
            raise HTTPException(status_code=400, detail="date is required for daily period.")
        return date_param, date_param

    if period == "weekly":
        if start_date is None:
            raise HTTPException(status_code=400, detail="start_date is required for weekly period.")
        week_start = get_week_start(start_date, settings.week_start_day)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    if period == "monthly":
        if year is None or month is None:
            raise HTTPException(
                status_code=400, detail="year and month required for monthly period."
            )
        from calendar import monthrange

        last_day = monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    if period == "yearly":
        if year is None:
            raise HTTPException(status_code=400, detail="year is required for yearly period.")
        return date(year, 1, 1), date(year, 12, 31)

    if period == "custom":
        if start_date is None or end_date is None:
            raise HTTPException(
                status_code=400, detail="start_date and end_date required for custom period."
            )
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be >= start_date.")
        return start_date, end_date

    raise HTTPException(status_code=400, detail=f"Unknown period: {period}")


@router.get(
    "/attendance",
    summary="Attendance report (all period types)",
    description=(
        "Generate an attendance compliance report. "
        "Supports period=daily|weekly|monthly|yearly|custom. "
        "This is the single primary reporting endpoint for all period types."
    ),
)
async def get_attendance_report(
    period: str = Query(..., description="Report period: daily|weekly|monthly|yearly|custom"),
    date: date | None = Query(default=None, description="Date for daily period (YYYY-MM-DD)"),
    start_date: date | None = Query(default=None, description="Start date for weekly/custom"),
    end_date: date | None = Query(default=None, description="End date for custom period"),
    year: int | None = Query(default=None, ge=2000, le=2100, description="Year for monthly/yearly"),
    month: int | None = Query(default=None, ge=1, le=12, description="Month for monthly"),
    department: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    employee_id: str | None = Query(default=None, description="Filter by employee ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    report_service: ReportService = Depends(get_report_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    if period not in ("daily", "weekly", "monthly", "yearly", "custom"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="period must be one of: daily, weekly, monthly, yearly, custom",
        )

    settings = get_settings()
    period_start, period_end = _resolve_period_dates(
        period, date, start_date, end_date, year, month, settings
    )

    # Enforce max date range
    if (period_end - period_start).days > settings.max_report_date_range_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Date range exceeds maximum of {settings.max_report_date_range_days} days."),
        )

    target_emp_id = employee_id
    if current_admin.get("role") == "employee":
        target_emp_id = current_admin.get("employee_id") or current_admin.get("admin_id")

    return await report_service.generate_report(
        period_start=period_start,
        period_end=period_end,
        period=period,
        department=department,
        is_active=is_active,
        employee_id=target_emp_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/attendance/export.csv",
    summary="Export attendance as CSV",
    description=(
        "Export attendance data as a downloadable CSV file. "
        "Accepts the same filters as the JSON endpoint. "
        "Sanitized against CSV formula injection."
    ),
)
async def export_attendance_csv(
    period: str = Query(...),
    date: date | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    department: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    report_service: ReportService = Depends(get_report_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> StreamingResponse:
    if period not in ("daily", "weekly", "monthly", "yearly", "custom"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="period must be one of: daily, weekly, monthly, yearly, custom",
        )

    settings = get_settings()
    period_start, period_end = _resolve_period_dates(
        period, date, start_date, end_date, year, month, settings
    )

    if (period_end - period_start).days > settings.max_report_date_range_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Date range exceeds maximum of {settings.max_report_date_range_days} days.",
        )

    target_emp_id = employee_id
    if current_admin.get("role") == "employee":
        target_emp_id = current_admin.get("employee_id") or current_admin.get("admin_id")

    report = await report_service.generate_report(
        period_start=period_start,
        period_end=period_end,
        period=period,
        department=department,
        is_active=is_active,
        employee_id=target_emp_id,
        page=1,
        page_size=10_000,  # Export all
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)

    # Header
    writer.writerow(
        [
            "Employee ID",
            "Name",
            "Email",
            "Department",
            "Is Active",
            "Total Days Attended",
            "Total Valid Hours",
            "Avg Hours/Day",
            "Completed Sessions",
            "Incomplete Sessions",
            "Invalid Sessions",
            "Has No Attendance",
            "Compliance Period",
            "Week Start",
            "Week End",
            "Is Evaluable",
            "Is Compliant",
            "Violation Reasons",
            "Approved Leave Dates",
            "Holiday Dates",
            "Total Late Minutes",
            "Total Early Exit Minutes",
            "Total Overtime Hours",
        ]
    )

    for emp in report["employees"]:
        weekly = emp.get("weekly_compliance", [])
        if weekly:
            for w in weekly:
                violations = "; ".join(w.get("violation_reasons", []))
                writer.writerow(
                    [
                        _csv_safe(emp["employee_id"]),
                        _csv_safe(emp["name"]),
                        _csv_safe(emp["email"]),
                        _csv_safe(emp["department"]),
                        emp["is_active"],
                        emp["total_days_attended"],
                        emp["total_valid_hours"],
                        emp["avg_hours_per_attended_day"],
                        emp["completed_sessions"],
                        emp["incomplete_sessions"],
                        emp["invalid_sessions"],
                        emp["has_no_attendance"],
                        period,
                        w.get("week_start", ""),
                        w.get("week_end", ""),
                        w.get("is_evaluable", ""),
                        w.get("is_compliant", ""),
                        _csv_safe(violations),
                        "; ".join(emp.get("approved_leave_dates", [])),
                        "; ".join(emp.get("holiday_dates", [])),
                        emp.get("total_late_minutes", 0),
                        emp.get("total_early_exit_minutes", 0),
                        emp.get("total_overtime_hours", 0.0),
                    ]
                )
        else:
            writer.writerow(
                [
                    _csv_safe(emp["employee_id"]),
                    _csv_safe(emp["name"]),
                    _csv_safe(emp["email"]),
                    _csv_safe(emp["department"]),
                    emp["is_active"],
                    emp["total_days_attended"],
                    emp["total_valid_hours"],
                    emp["avg_hours_per_attended_day"],
                    emp["completed_sessions"],
                    emp["incomplete_sessions"],
                    emp["invalid_sessions"],
                    emp["has_no_attendance"],
                    period,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    emp.get("total_late_minutes", 0),
                    emp.get("total_early_exit_minutes", 0),
                    emp.get("total_overtime_hours", 0.0),
                ]
            )

    output.seek(0)
    filename = f"attendance_{period}_{period_start}_{period_end}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
