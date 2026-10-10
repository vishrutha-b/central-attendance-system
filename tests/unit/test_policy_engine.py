"""
Unit tests for deterministic Attendance Policy Engine (policy_service.py).

Verifies compliance calculations, session interval merging, partial week handling,
leave/holiday adjustments, and violation reason tagging.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.services.policy_service import (
    PolicyThresholds,
    WeekBoundary,
    calculate_adjusted_thresholds,
    calculate_valid_hours_for_sessions,
    evaluate_week,
    get_week_boundary,
    is_week_complete,
    merge_intervals,
    parse_session,
)

TZ_KOLKATA = ZoneInfo("Asia/Kolkata")


def make_dt(d: date, hour: int, minute: int = 0) -> datetime:
    """Helper to construct UTC datetime for a local Kolkata time."""
    return datetime.combine(d, time(hour, minute), tzinfo=TZ_KOLKATA).astimezone(UTC)


def test_merge_intervals_non_overlapping():
    intervals = [(10.0, 12.0), (13.0, 15.0)]
    merged = merge_intervals(intervals)
    assert merged == [(10.0, 12.0), (13.0, 15.0)]


def test_merge_intervals_overlapping():
    intervals = [(10.0, 14.0), (12.0, 16.0)]
    merged = merge_intervals(intervals)
    assert merged == [(10.0, 16.0)]


def test_merge_intervals_contained():
    intervals = [(9.0, 17.0), (10.0, 12.0), (13.0, 15.0)]
    merged = merge_intervals(intervals)
    assert merged == [(9.0, 17.0)]


def test_calculate_valid_hours_with_overlapping_sessions():
    d = date(2026, 1, 12)
    s1 = parse_session(
        {
            "attendance_id": "1",
            "date": d.isoformat(),
            "entry_time": make_dt(d, 9, 0),
            "exit_time": make_dt(d, 13, 0),  # 4 hours
        }
    )
    s2 = parse_session(
        {
            "attendance_id": "2",
            "date": d.isoformat(),
            "entry_time": make_dt(d, 12, 0),
            "exit_time": make_dt(d, 17, 0),  # 5 hours, 1 hr overlap
        }
    )
    # Total distinct span: 9:00 to 17:00 = 8.0 hours
    total = calculate_valid_hours_for_sessions([s1, s2])
    assert pytest.approx(total, 0.01) == 8.0


def test_incomplete_session_contributes_zero_hours():
    d = date(2026, 1, 12)
    s = parse_session(
        {
            "attendance_id": "inc",
            "date": d.isoformat(),
            "entry_time": make_dt(d, 9, 0),
            "exit_time": None,
        }
    )
    assert s.is_complete is False
    assert s.hours == 0.0


def test_invalid_session_exit_before_entry():
    d = date(2026, 1, 12)
    s = parse_session(
        {
            "attendance_id": "inv",
            "date": d.isoformat(),
            "entry_time": make_dt(d, 17, 0),
            "exit_time": make_dt(d, 9, 0),
        }
    )
    assert s.is_invalid is True
    assert s.hours == 0.0


def test_week_boundary_calculation():
    # 2026-01-14 is Wednesday
    d = date(2026, 1, 14)
    wb = get_week_boundary(d, week_start_day=0)  # Monday start
    assert wb.start == date(2026, 1, 12)
    assert wb.end == date(2026, 1, 19)


def test_is_week_complete():
    wb = WeekBoundary(start=date(2026, 1, 12), end=date(2026, 1, 19))
    assert is_week_complete(wb, today=date(2026, 1, 18)) is False
    assert is_week_complete(wb, today=date(2026, 1, 19)) is True
    assert is_week_complete(wb, today=date(2026, 1, 20)) is True


def test_evaluate_week_fully_compliant():
    week = WeekBoundary(start=date(2026, 1, 12), end=date(2026, 1, 19))
    thresholds = PolicyThresholds(
        min_days_per_week=3, min_hours_per_week=15.0, min_avg_hours_per_day=5.0
    )

    # 4 days, 6 hours each day = 24 hours, avg 6.0
    sessions = []
    for i in range(4):
        d = week.start + timedelta(days=i)
        sessions.append(
            {
                "attendance_id": f"s-{i}",
                "date": d.isoformat(),
                "entry_time": make_dt(d, 9, 0),
                "exit_time": make_dt(d, 15, 0),
            }
        )

    result = evaluate_week(
        week=week,
        sessions=sessions,
        thresholds=thresholds,
        today=date(2026, 1, 25),  # Complete week
    )

    assert result.is_evaluable is True
    assert result.is_compliant is True
    assert result.days_attended == 4
    assert pytest.approx(result.total_hours, 0.01) == 24.0
    assert pytest.approx(result.avg_hours_per_day, 0.01) == 6.0
    assert len(result.violation_reasons) == 0


def test_evaluate_week_violations_detected():
    week = WeekBoundary(start=date(2026, 1, 12), end=date(2026, 1, 19))
    thresholds = PolicyThresholds(
        min_days_per_week=3, min_hours_per_week=15.0, min_avg_hours_per_day=5.0
    )

    # Only 2 days, 4 hours each = 8 hours total (< 3 days, < 15 hrs, < 5 avg)
    sessions = [
        {
            "attendance_id": "s-0",
            "date": week.start.isoformat(),
            "entry_time": make_dt(week.start, 10, 0),
            "exit_time": make_dt(week.start, 14, 0),
        },
        {
            "attendance_id": "s-1",
            "date": (week.start + timedelta(days=1)).isoformat(),
            "entry_time": make_dt(week.start + timedelta(days=1), 10, 0),
            "exit_time": make_dt(week.start + timedelta(days=1), 14, 0),
        },
    ]

    result = evaluate_week(
        week=week,
        sessions=sessions,
        thresholds=thresholds,
        today=date(2026, 1, 25),
    )

    assert result.is_evaluable is True
    assert result.is_compliant is False
    assert result.days_attended == 2
    assert pytest.approx(result.total_hours, 0.01) == 8.0
    assert len(result.violation_reasons) > 0
    # Checks specific violation mentions
    assert any("attended" in r.lower() for r in result.violation_reasons)
    assert any("hours" in r.lower() for r in result.violation_reasons)


def test_adjusted_thresholds_with_holidays_and_leave():
    week = WeekBoundary(start=date(2026, 1, 12), end=date(2026, 1, 19))
    thresholds = PolicyThresholds(
        min_days_per_week=3, min_hours_per_week=15.0, working_days_per_week=5
    )

    # 1 holiday + 1 approved leave -> 2 excused out of 5 working days -> 3 eligible days remaining
    holidays = {date(2026, 1, 15)}
    leaves = {date(2026, 1, 16)}

    adj_days, adj_hours, eligible_days, hol_cnt, lv_cnt = calculate_adjusted_thresholds(
        week, thresholds, holidays, leaves
    )

    assert eligible_days == 3
    assert hol_cnt == 1
    assert lv_cnt == 1
    # 3 eligible / 5 working = ratio 0.6
    # adj_days = ceil(3 * 0.6) = ceil(1.8) = 2
    assert adj_days == 2
    # adj_hours = 15.0 * 0.6 = 9.0
    assert pytest.approx(adj_hours, 0.01) == 9.0
