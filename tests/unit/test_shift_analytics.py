"""Unit tests for shift analytics (late-in, early-exit, overtime)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.services.policy_service import calculate_shift_metrics


def test_calculate_shift_metrics_on_time():
    # 09:30 AM entry, 18:30 PM exit (local Asia/Kolkata is UTC+05:30)
    # 09:30 local = 04:00 UTC
    # 18:30 local = 13:00 UTC
    sessions = [
        {
            "attendance_id": "ATT-1",
            "date": date(2026, 4, 1),
            "entry_time": datetime(2026, 4, 1, 4, 0, tzinfo=UTC),
            "exit_time": datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
        }
    ]
    metrics = calculate_shift_metrics(
        sessions,
        shift_start_str="09:30",
        shift_end_str="18:30",
        late_grace_minutes=15,
        standard_shift_hours=8.0,
        company_tz_name="Asia/Kolkata",
    )
    assert metrics["is_late"] is False
    assert metrics["late_minutes"] == 0
    assert metrics["is_early_exit"] is False
    assert metrics["early_exit_minutes"] == 0
    assert metrics["overtime_hours"] == 1.0  # 9 hours total - 8h standard = 1h OT


def test_calculate_shift_metrics_late_and_early_exit():
    # 10:15 local = 04:45 UTC (45 mins after 09:30, grace is 15 mins -> 45 mins late)
    # 17:30 local = 12:00 UTC (60 mins before 18:30 -> 60 mins early exit)
    sessions = [
        {
            "attendance_id": "ATT-2",
            "date": date(2026, 4, 1),
            "entry_time": datetime(2026, 4, 1, 4, 45, tzinfo=UTC),
            "exit_time": datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
        }
    ]
    metrics = calculate_shift_metrics(
        sessions,
        shift_start_str="09:30",
        shift_end_str="18:30",
        late_grace_minutes=15,
        standard_shift_hours=8.0,
        company_tz_name="Asia/Kolkata",
    )
    assert metrics["is_late"] is True
    assert metrics["late_minutes"] == 45
    assert metrics["is_early_exit"] is True
    assert metrics["early_exit_minutes"] == 60
    assert metrics["overtime_hours"] == 0.0


def test_calculate_shift_metrics_within_grace_period():
    # 09:40 local = 04:10 UTC (10 mins after 09:30, grace is 15 mins -> NOT late)
    sessions = [
        {
            "attendance_id": "ATT-3",
            "date": date(2026, 4, 1),
            "entry_time": datetime(2026, 4, 1, 4, 10, tzinfo=UTC),
            "exit_time": datetime(2026, 4, 1, 13, 0, tzinfo=UTC),
        }
    ]
    metrics = calculate_shift_metrics(
        sessions,
        shift_start_str="09:30",
        shift_end_str="18:30",
        late_grace_minutes=15,
        standard_shift_hours=8.0,
        company_tz_name="Asia/Kolkata",
    )
    assert metrics["is_late"] is False
    assert metrics["late_minutes"] == 0
