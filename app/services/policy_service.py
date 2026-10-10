"""
Attendance Policy Service — deterministic, stateless compliance calculator.

This module has NO dependency on FastAPI, email, or any I/O.
It operates purely on attendance session data and configuration.

Default Policy (all thresholds configurable):
  - MIN_DAYS_PER_WEEK  = 3   distinct qualifying days
  - MIN_HOURS_PER_WEEK = 15  valid office hours
  - MIN_AVG_HOURS_PER_DAY = 5  average hours per qualifying day

Definitions:
  - A "qualifying day" = a calendar date with at least one COMPLETE session.
  - A "complete session" = entry AND exit recorded, exit > entry.
  - Hours from overlapping sessions are de-duplicated using interval merging.
  - An incomplete session (missing exit) contributes 0 hours.
  - Weekend and holiday dates reduce expected thresholds proportionally.
  - Approved leave further reduces required attendance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PolicyThresholds:
    min_days_per_week: int = 3
    min_hours_per_week: float = 15.0
    min_avg_hours_per_day: float = 5.0
    working_days_per_week: int = 5
    week_start_day: int = 0  # 0=Monday


@dataclass
class WeekBoundary:
    start: date  # inclusive
    end: date  # exclusive (next week's Monday)


@dataclass
class SessionStats:
    """Processed stats for one attendance session."""

    attendance_id: str
    attendance_date: date
    entry_time: datetime
    exit_time: datetime | None
    hours: float  # 0 if incomplete
    is_complete: bool
    is_invalid: bool  # exit before entry


@dataclass
class WeeklyComplianceResult:
    week_start: date
    week_end: date  # exclusive
    is_evaluable: bool  # True = week is complete
    is_compliant: bool | None  # None = cannot evaluate yet
    days_attended: int
    total_hours: float
    avg_hours_per_day: float
    completed_sessions: int
    incomplete_sessions: int
    invalid_sessions: int
    violation_reasons: list[str] = field(default_factory=list)
    eligible_working_days: int = 0
    adjusted_min_days: int = 0
    adjusted_min_hours: float = 0.0
    approved_leave_days: int = 0
    holiday_days: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Week boundary utilities
# ─────────────────────────────────────────────────────────────────────────────


def get_week_start(d: date, week_start_day: int = 0) -> date:
    """Return the Monday (or configured start) of the week containing d."""
    days_since_start = (d.weekday() - week_start_day) % 7
    return d - timedelta(days=days_since_start)


def get_week_boundary(d: date, week_start_day: int = 0) -> WeekBoundary:
    """Return the [start, end) boundary of the policy week containing d."""
    start = get_week_start(d, week_start_day)
    end = start + timedelta(days=7)
    return WeekBoundary(start=start, end=end)


def get_all_weeks_in_range(start: date, end: date, week_start_day: int = 0) -> list[WeekBoundary]:
    """Return all distinct policy week boundaries that overlap [start, end]."""
    weeks: list[WeekBoundary] = []
    seen: set[date] = set()
    current = start
    while current <= end:
        wb = get_week_boundary(current, week_start_day)
        if wb.start not in seen:
            seen.add(wb.start)
            weeks.append(wb)
        current += timedelta(days=7)
    return weeks


def is_week_complete(week: WeekBoundary, today: date) -> bool:
    """A week is complete when today is on or after the week's exclusive end."""
    return today >= week.end


# ─────────────────────────────────────────────────────────────────────────────
# Session processing
# ─────────────────────────────────────────────────────────────────────────────


def parse_session(record: dict[str, Any]) -> SessionStats:
    """Convert a raw MongoDB attendance document into a SessionStats object."""
    entry_time: datetime = record["entry_time"]
    exit_time: datetime | None = record.get("exit_time")
    att_date_raw = record.get("date")

    if isinstance(att_date_raw, str):
        att_date = date.fromisoformat(att_date_raw)
    elif isinstance(att_date_raw, date):
        att_date = att_date_raw
    else:
        att_date = entry_time.date()

    is_invalid = False
    is_complete = False
    hours = 0.0

    if exit_time is not None:
        if exit_time <= entry_time:
            is_invalid = True
            hours = 0.0
        else:
            is_complete = True
            delta_seconds = (exit_time - entry_time).total_seconds()
            hours = delta_seconds / 3600.0

    return SessionStats(
        attendance_id=record.get("attendance_id", ""),
        attendance_date=att_date,
        entry_time=entry_time,
        exit_time=exit_time,
        hours=hours,
        is_complete=is_complete,
        is_invalid=is_invalid,
    )


def merge_intervals(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Merge overlapping time intervals to prevent double-counting.
    Each interval is (start_seconds, end_seconds) since epoch.
    Returns merged, non-overlapping intervals sorted by start.
    """
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current_start, current_end in sorted_intervals[1:]:
        last_start, last_end = merged[-1]
        if current_start <= last_end:
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged


def calculate_valid_hours_for_sessions(sessions: list[SessionStats]) -> float:
    """
    Calculate de-duplicated valid office hours from a list of sessions.
    Overlapping intervals are merged before summing.
    Only complete (non-invalid) sessions contribute.
    """
    intervals: list[tuple[float, float]] = []
    for s in sessions:
        if s.is_complete and not s.is_invalid and s.exit_time is not None:
            start_ts = s.entry_time.timestamp()
            end_ts = s.exit_time.timestamp()
            intervals.append((start_ts, end_ts))

    merged = merge_intervals(intervals)
    total_seconds = sum(end - start for start, end in merged)
    return total_seconds / 3600.0


# ─────────────────────────────────────────────────────────────────────────────
# Threshold adjustment for leave/holidays
# ─────────────────────────────────────────────────────────────────────────────


def _get_working_dates_in_week(week: WeekBoundary, working_days_per_week: int) -> list[date]:
    """
    Return working dates in the week (Mon–Fri by default).
    Week is [week.start, week.end).
    """
    all_dates = [week.start + timedelta(days=i) for i in range(7)]
    # Working days are the first `working_days_per_week` days of the week
    return all_dates[:working_days_per_week]


def calculate_adjusted_thresholds(
    week: WeekBoundary,
    thresholds: PolicyThresholds,
    holiday_dates: set[date],
    approved_leave_dates: set[date],
) -> tuple[int, float, int, int, int]:
    """
    Calculate adjusted minimum days and hours for a week given holidays and leave.

    Returns:
        (adjusted_min_days, adjusted_min_hours, eligible_working_days,
         holiday_count, leave_count)

    Rounding rule:
        adjusted_min_days is rounded UP (ceiling) to ensure we never
        require more days than exist. adjusted_min_hours uses proportional
        floating-point calculation (no rounding — compared as float).
    """
    import math

    working_dates = _get_working_dates_in_week(week, thresholds.working_days_per_week)
    n_working = len(working_dates)

    excused = set()
    holiday_count = 0
    leave_count = 0
    for d in working_dates:
        if d in holiday_dates:
            excused.add(d)
            holiday_count += 1
        elif d in approved_leave_dates:
            excused.add(d)
            leave_count += 1

    eligible_days = n_working - len(excused)

    if eligible_days <= 0:
        # Full week excused
        return 0, 0.0, 0, holiday_count, leave_count

    ratio = eligible_days / n_working

    # Proportional thresholds, minimum 0
    adj_days = max(0, math.ceil(thresholds.min_days_per_week * ratio))
    adj_hours = max(0.0, thresholds.min_hours_per_week * ratio)

    # Cannot require more days than there are eligible working days
    adj_days = min(adj_days, eligible_days)

    return adj_days, adj_hours, eligible_days, holiday_count, leave_count


# ─────────────────────────────────────────────────────────────────────────────
# Core compliance calculator
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_week(
    week: WeekBoundary,
    sessions: list[dict[str, Any]],
    thresholds: PolicyThresholds,
    today: date,
    holiday_dates: set[date] | None = None,
    approved_leave_dates: set[date] | None = None,
    force_evaluable: bool = False,
) -> WeeklyComplianceResult:
    """
    Evaluate compliance for one policy week.

    Args:
        week: The WeekBoundary being evaluated.
        sessions: Raw attendance documents for this employee in this week.
        thresholds: Policy configuration.
        today: Reference date to determine if the week is complete.
        holiday_dates: Set of company holiday dates.
        approved_leave_dates: Set of approved leave dates for this employee.
        force_evaluable: If True, evaluates compliance even if the week is still in progress.

    Returns:
        WeeklyComplianceResult with full compliance details.
    """
    holiday_dates = holiday_dates or set()
    approved_leave_dates = approved_leave_dates or set()
    evaluable = is_week_complete(week, today) or force_evaluable

    parsed = [parse_session(s) for s in sessions]
    # Only count sessions that fall within the week boundary
    week_sessions = [s for s in parsed if week.start <= s.attendance_date < week.end]

    completed = [s for s in week_sessions if s.is_complete]
    incomplete = [s for s in week_sessions if not s.is_complete and not s.is_invalid]
    invalid = [s for s in week_sessions if s.is_invalid]

    # Distinct days with at least one complete session
    qualifying_days: set[date] = {s.attendance_date for s in completed}
    days_attended = len(qualifying_days)

    # De-duplicated hours
    total_hours = calculate_valid_hours_for_sessions(completed)
    avg_hours = total_hours / days_attended if days_attended > 0 else 0.0

    # Adjust thresholds for holidays and leave
    adj_days, adj_hours, eligible_days, holiday_count, leave_count = calculate_adjusted_thresholds(
        week, thresholds, holiday_dates, approved_leave_dates
    )

    violations: list[str] = []
    is_compliant: bool | None = None

    if not evaluable:
        # Cannot make a compliance determination for incomplete weeks
        is_compliant = None
    elif eligible_days == 0:
        # Fully excused week — compliant by default
        is_compliant = True
    else:
        is_compliant = True

        # Rule 1: Minimum qualifying days
        if days_attended < adj_days:
            is_compliant = False
            violations.append(
                f"Attended {days_attended} day{'s' if days_attended != 1 else ''}; "
                f"{adj_days} day{'s' if adj_days != 1 else ''} required."
            )

        # Rule 2: Minimum total hours
        if total_hours < adj_hours:
            is_compliant = False
            violations.append(f"Completed {total_hours:.1f} hours; {adj_hours:.1f} hours required.")

        # Rule 3: Average hours per day
        if days_attended > 0 and avg_hours < thresholds.min_avg_hours_per_day:
            is_compliant = False
            violations.append(
                f"Average attendance was {avg_hours:.1f} hours per attended day; "
                f"{thresholds.min_avg_hours_per_day:.1f} hours required."
            )

        # Informational: incomplete sessions present
        if incomplete and is_compliant:
            violations.append(f"{len(incomplete)} session(s) incomplete (exit time missing).")

        # No attendance at all
        if (
            days_attended == 0
            and eligible_days > 0
            and not any("Attended 0" in v for v in violations)
        ):
            violations.append("No attendance recorded during the relevant period.")

    return WeeklyComplianceResult(
        week_start=week.start,
        week_end=week.end,
        is_evaluable=evaluable,
        is_compliant=is_compliant,
        days_attended=days_attended,
        total_hours=round(total_hours, 4),
        avg_hours_per_day=round(avg_hours, 4),
        completed_sessions=len(completed),
        incomplete_sessions=len(incomplete),
        invalid_sessions=len(invalid),
        violation_reasons=violations,
        eligible_working_days=eligible_days,
        adjusted_min_days=adj_days,
        adjusted_min_hours=round(adj_hours, 4),
        approved_leave_days=leave_count,
        holiday_days=holiday_count,
    )


def evaluate_period(
    start: date,
    end: date,
    sessions: list[dict[str, Any]],
    thresholds: PolicyThresholds,
    today: date,
    holiday_dates: set[date] | None = None,
    approved_leave_dates: set[date] | None = None,
) -> list[WeeklyComplianceResult]:
    """
    Evaluate all policy weeks within [start, end] for an employee.

    Returns a list of WeeklyComplianceResult, one per week.
    """
    holiday_dates = holiday_dates or set()
    approved_leave_dates = approved_leave_dates or set()
    weeks = get_all_weeks_in_range(start, end, thresholds.week_start_day)
    results = []
    for week in weeks:
        # Filter sessions to this week
        week_sessions = [s for s in sessions if _session_in_week(s, week)]
        result = evaluate_week(
            week=week,
            sessions=week_sessions,
            thresholds=thresholds,
            today=today,
            holiday_dates=holiday_dates,
            approved_leave_dates=approved_leave_dates,
        )
        results.append(result)
    return results


def _session_in_week(session: dict[str, Any], week: WeekBoundary) -> bool:
    """Check if a raw session falls within the week boundary."""
    date_raw = session.get("date")
    if isinstance(date_raw, str):
        try:
            d = date.fromisoformat(date_raw)
        except ValueError:
            return False
    elif isinstance(date_raw, date):
        d = date_raw
    else:
        return False
    return week.start <= d < week.end


def calculate_overall_stats(
    sessions: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Calculate overall attendance statistics across all sessions.
    Used for non-week-aligned reports (daily, monthly, yearly, custom).
    """
    parsed = [parse_session(s) for s in sessions]
    completed = [s for s in parsed if s.is_complete]
    incomplete = [s for s in parsed if not s.is_complete and not s.is_invalid]
    invalid = [s for s in parsed if s.is_invalid]

    qualifying_days: set[date] = {s.attendance_date for s in completed}
    days_attended = len(qualifying_days)
    total_hours = calculate_valid_hours_for_sessions(completed)
    avg_hours = total_hours / days_attended if days_attended > 0 else 0.0

    return {
        "days_attended": days_attended,
        "total_hours": round(total_hours, 4),
        "avg_hours_per_attended_day": round(avg_hours, 4),
        "completed_sessions": len(completed),
        "incomplete_sessions": len(incomplete),
        "invalid_sessions": len(invalid),
        "has_no_attendance": len(parsed) == 0,
    }
