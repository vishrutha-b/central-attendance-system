"""Report generation service — powers both JSON and CSV endpoints."""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any

from app.config import get_settings
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.employee_repo import EmployeeRepository
from app.services.leave_service import HolidayService, LeaveService
from app.services.policy_service import (
    PolicyThresholds,
    calculate_overall_stats,
    calculate_shift_metrics,
    evaluate_period,
)

logger = logging.getLogger(__name__)


def _build_thresholds() -> PolicyThresholds:
    s = get_settings()
    return PolicyThresholds(
        min_days_per_week=s.min_days_per_week,
        min_hours_per_week=s.min_hours_per_week,
        min_avg_hours_per_day=s.min_avg_hours_per_day,
        working_days_per_week=s.working_days_per_week,
        week_start_day=s.week_start_day,
    )


class ReportService:
    def __init__(
        self,
        employee_repo: EmployeeRepository,
        attendance_repo: AttendanceRepository,
        leave_service: LeaveService,
        holiday_service: HolidayService,
    ) -> None:
        self.employee_repo = employee_repo
        self.attendance_repo = attendance_repo
        self.leave_service = leave_service
        self.holiday_service = holiday_service

    async def generate_report(
        self,
        period_start: date,
        period_end: date,
        period: str,
        department: str | None = None,
        is_active: bool | None = None,
        employee_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Generate attendance report for all employees in the given range."""
        settings = get_settings()
        thresholds = _build_thresholds()
        today = date.today()

        # Load employees with filters
        if employee_id:
            emp = await self.employee_repo.find_by_id(employee_id.upper())
            all_employees = [emp] if emp else []
            total = len(all_employees)
        else:
            all_employees, total = await self.employee_repo.list_employees(
                skip=0,
                limit=10_000,  # load all, we paginate after
                department=department,
                is_active=is_active,
            )

        # Load company holidays
        holiday_dates = await self.holiday_service.get_holiday_dates(period_start, period_end)

        # Build per-employee report data
        employee_reports: list[dict[str, Any]] = []
        for emp in all_employees:
            emp_id = emp["employee_id"]

            # Load attendance sessions
            sessions = await self.attendance_repo.find_sessions_in_range(
                emp_id, period_start, period_end
            )

            # Load approved leave dates
            approved_leave_dates = await self.leave_service.get_approved_leave_dates(
                emp_id, period_start, period_end
            )

            # Overall stats (for non-weekly summaries)
            overall = calculate_overall_stats(sessions)

            # Weekly compliance evaluation
            weekly_results = evaluate_period(
                start=period_start,
                end=period_end,
                sessions=sessions,
                thresholds=thresholds,
                today=today,
                holiday_dates=holiday_dates,
                approved_leave_dates=approved_leave_dates,
            )

            # Missing attendance dates (working days with no sessions)
            all_session_dates = {
                date.fromisoformat(s["date"]) if isinstance(s["date"], str) else s["date"]
                for s in sessions
            }
            missing_dates = _calculate_missing_dates(
                period_start,
                period_end,
                all_session_dates,
                holiday_dates,
                approved_leave_dates,
                settings.week_start_day,
                settings.working_days_per_week,
            )

            # Calculate shift metrics across period
            total_late_mins = 0
            total_early_mins = 0
            total_ot_hours = 0.0

            sessions_by_date: dict[str, list[dict[str, Any]]] = {}
            for s in sessions:
                d_str = s["date"].isoformat() if isinstance(s["date"], date) else str(s["date"])
                sessions_by_date.setdefault(d_str, []).append(s)

            for _d_str, day_sessions in sessions_by_date.items():
                s_metrics = calculate_shift_metrics(
                    day_sessions,
                    shift_start_str=settings.shift_start_time,
                    shift_end_str=settings.shift_end_time,
                    late_grace_minutes=settings.late_grace_minutes,
                    standard_shift_hours=settings.standard_shift_hours,
                    company_tz_name=settings.company_timezone,
                )
                total_late_mins += s_metrics["late_minutes"]
                total_early_mins += s_metrics["early_exit_minutes"]
                total_ot_hours += s_metrics["overtime_hours"]

            employee_reports.append(
                {
                    "employee_id": emp_id,
                    "name": emp["name"],
                    "email": emp["email"],
                    "department": emp["department"],
                    "is_active": emp["is_active"],
                    "total_days_attended": overall["days_attended"],
                    "total_valid_hours": overall["total_hours"],
                    "avg_hours_per_attended_day": overall["avg_hours_per_attended_day"],
                    "completed_sessions": overall["completed_sessions"],
                    "incomplete_sessions": overall["incomplete_sessions"],
                    "invalid_sessions": overall["invalid_sessions"],
                    "missing_dates": [d.isoformat() for d in sorted(missing_dates)],
                    "approved_leave_dates": [d.isoformat() for d in sorted(approved_leave_dates)],
                    "holiday_dates": [d.isoformat() for d in sorted(holiday_dates)],
                    "weekly_compliance": [
                        {
                            "week_start": r.week_start.isoformat(),
                            "week_end": r.week_end.isoformat(),
                            "is_evaluable": r.is_evaluable,
                            "is_compliant": r.is_compliant,
                            "days_attended": r.days_attended,
                            "total_hours": r.total_hours,
                            "avg_hours_per_day": r.avg_hours_per_day,
                            "completed_sessions": r.completed_sessions,
                            "incomplete_sessions": r.incomplete_sessions,
                            "violation_reasons": r.violation_reasons,
                            "eligible_working_days": r.eligible_working_days,
                            "adjusted_min_days": r.adjusted_min_days,
                            "adjusted_min_hours": r.adjusted_min_hours,
                        }
                        for r in weekly_results
                    ],
                    "has_no_attendance": overall["has_no_attendance"],
                    "total_late_minutes": total_late_mins,
                    "total_early_exit_minutes": total_early_mins,
                    "total_overtime_hours": round(total_ot_hours, 2),
                }
            )

        # Paginate
        total_employees = len(employee_reports)
        skip = (page - 1) * page_size
        paginated = employee_reports[skip : skip + page_size]
        total_pages = max(1, math.ceil(total_employees / page_size)) if page_size > 0 else 1

        # Company summary
        summary = _build_company_summary(
            employee_reports, period_start, period_end, settings.company_timezone
        )

        return {
            "period": period,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "timezone": settings.company_timezone,
            "employees": paginated,
            "company_summary": summary,
            "page": page,
            "page_size": page_size,
            "total": total_employees,
            "total_pages": total_pages,
        }


def _calculate_missing_dates(
    start: date,
    end: date,
    session_dates: set[date],
    holiday_dates: set[date],
    approved_leave_dates: set[date],
    week_start_day: int,
    working_days_per_week: int,
) -> list[date]:
    """Return working dates in the range where no attendance was recorded."""
    missing = []
    current = start
    while current <= end:
        weekday = (current.weekday() - week_start_day) % 7
        is_working_day = weekday < working_days_per_week
        if (
            is_working_day
            and current not in session_dates
            and current not in holiday_dates
            and current not in approved_leave_dates
        ):
            missing.append(current)
        current += timedelta(days=1)
    return missing


def _build_company_summary(
    reports: list[dict[str, Any]],
    period_start: date,
    period_end: date,
    timezone: str,
) -> dict[str, Any]:
    total = len(reports)
    compliant = 0
    non_compliant = 0
    no_attendance = 0
    incomplete_attendance = 0
    pending_evaluation = 0
    total_hours = 0.0

    for r in reports:
        total_hours += r["total_valid_hours"]
        if r["has_no_attendance"]:
            no_attendance += 1

        if r["incomplete_sessions"] > 0 and r["completed_sessions"] == 0:
            incomplete_attendance += 1

        # Compliance determination across all weeks
        weekly = r["weekly_compliance"]
        if not weekly:
            pending_evaluation += 1
            continue

        evaluable_weeks = [w for w in weekly if w["is_evaluable"]]
        if not evaluable_weeks:
            pending_evaluation += 1
            continue

        violations_found = any(w["is_compliant"] is False for w in evaluable_weeks)
        if violations_found:
            non_compliant += 1
        else:
            compliant += 1

    avg_hours = total_hours / total if total > 0 else 0.0

    return {
        "total_employees": total,
        "compliant_count": compliant,
        "non_compliant_count": non_compliant,
        "no_attendance_count": no_attendance,
        "incomplete_attendance_count": incomplete_attendance,
        "pending_evaluation_count": pending_evaluation,
        "total_valid_hours": round(total_hours, 4),
        "avg_hours_per_employee": round(avg_hours, 4),
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "timezone": timezone,
    }
