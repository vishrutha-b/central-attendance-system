"""
Attendance monitoring worker.

Identifies completed policy weeks, evaluates compliance, and sends
violation notifications with deduplication and retry logic.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.config import get_settings
from app.repositories.admin_repo import AuditRepository, NotificationRepository
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.leave_repo import HolidayRepository, LeaveRepository
from app.services.audit_service import AuditService
from app.services.leave_service import HolidayService, LeaveService
from app.services.notification_service import NotificationService
from app.services.policy_service import (
    PolicyThresholds,
    evaluate_week,
    is_week_complete,
)

logger = logging.getLogger(__name__)


async def run_monitoring_cycle(
    db: Any,
    include_current_week: bool = False,
    force_resend: bool = False,
) -> dict[str, Any]:
    """
    Run one monitoring cycle:
    1. Find all completed policy weeks in the past N weeks (optionally include current week)
    2. For each active employee, evaluate compliance
    3. Send violation notifications (with deduplication unless force_resend=True)
    4. Retry pending notifications that failed earlier

    Returns a summary dict with counts and violation details.
    """
    settings = get_settings()
    today = date.today()

    thresholds = PolicyThresholds(
        min_days_per_week=settings.min_days_per_week,
        min_hours_per_week=settings.min_hours_per_week,
        min_avg_hours_per_day=settings.min_avg_hours_per_day,
        working_days_per_week=settings.working_days_per_week,
        week_start_day=settings.week_start_day,
    )

    employee_repo = EmployeeRepository(db)
    attendance_repo = AttendanceRepository(db)
    leave_repo = LeaveRepository(db)
    holiday_repo = HolidayRepository(db)
    notification_repo = NotificationRepository(db)
    notification_svc = NotificationService()
    audit_repo = AuditRepository(db)
    audit_svc = AuditService(audit_repo)

    leave_svc = LeaveService(leave_repo, employee_repo, audit_svc)
    holiday_svc = HolidayService(holiday_repo)

    # Determine weeks to check (last 4 completed weeks)
    weeks_to_check = _get_completed_weeks(today, thresholds.week_start_day, lookback_weeks=4)

    from app.services.policy_service import get_week_boundary

    current_wb = get_week_boundary(today, thresholds.week_start_day)

    if include_current_week and not any(w.start == current_wb.start for w in weeks_to_check):
        weeks_to_check.insert(0, current_wb)

    if not weeks_to_check:
        logger.info("No policy weeks to evaluate.")
        return {
            "status": "no_completed_weeks",
            "checked": 0,
            "violations": 0,
            "sent": 0,
            "details": [],
        }

    logger.info(
        "Monitoring: checking %d weeks (include_current=%s).",
        len(weeks_to_check),
        include_current_week,
    )

    # Load all active employees
    employees = await employee_repo.get_active_employees()

    sent_count = 0
    violation_count = 0
    skipped_count = 0
    details: list[dict[str, Any]] = []

    for emp in employees:
        emp_id = emp["employee_id"]
        emp_email = emp["email"]
        emp_name = emp["name"]

        for week in weeks_to_check:
            dedup_key = f"{emp_id}::{week.start.isoformat()}::violation"

            # Check deduplication
            existing = await notification_repo.find_by_dedup_key(dedup_key)
            if existing and existing.get("status") in ("sent", "exhausted") and not force_resend:
                skipped_count += 1
                continue

            # Load sessions for this week
            sessions = await attendance_repo.find_sessions_in_range(
                emp_id, week.start, week.end - timedelta(days=1)
            )

            # Load holidays and leave
            holiday_dates = await holiday_svc.get_holiday_dates(
                week.start, week.end - timedelta(days=1)
            )
            approved_leave = await leave_svc.get_approved_leave_dates(
                emp_id, week.start, week.end - timedelta(days=1)
            )

            is_curr = week.start == current_wb.start
            result = evaluate_week(
                week=week,
                sessions=sessions,
                thresholds=thresholds,
                today=today,
                holiday_dates=holiday_dates,
                approved_leave_dates=approved_leave,
                force_evaluable=include_current_week and is_curr,
            )

            if not result.is_evaluable:
                continue

            if result.is_compliant is True:
                continue  # Compliant — no notification needed

            violation_count += 1

            # Handle retry or new notification
            if existing is None:
                # Create new notification log
                now = datetime.now(tz=UTC)
                notification_id = f"NTF-{uuid.uuid4().hex[:12].upper()}"
                notification_doc = {
                    "notification_id": notification_id,
                    "employee_id": emp_id,
                    "employee_email_snapshot": emp_email,
                    "period_start": week.start.isoformat(),
                    "period_end": (week.end - timedelta(days=1)).isoformat(),
                    "notification_type": "violation",
                    "violation_summary": result.violation_reasons,
                    "dedup_key": dedup_key,
                    "attempt_count": 0,
                    "status": "pending",
                    "last_attempt_at": None,
                    "next_retry_at": now,
                    "error_summary": None,
                    "created_at": now,
                    "updated_at": now,
                }
                notification_doc = await notification_repo.create(notification_doc)
                notification_id = notification_doc["notification_id"]
            else:
                notification_id = existing["notification_id"]

            # Attempt delivery
            attempt_count = (existing or {}).get("attempt_count", 0) + 1

            if attempt_count > settings.notification_max_retries + 1:
                await notification_repo.update(notification_id, {"status": "exhausted"})
                logger.warning("Notification exhausted for %s week %s", emp_id, week.start)
                continue

            success = await notification_svc.send_violation_email(
                employee_email=emp_email,
                employee_name=emp_name,
                employee_id=emp_id,
                department=emp.get("department", "General"),
                week_start=week.start.isoformat(),
                week_end=(week.end - timedelta(days=1)).isoformat(),
                violations=result.violation_reasons,
            )

            now = datetime.now(tz=UTC)
            if success:
                await notification_repo.update(
                    notification_id,
                    {
                        "status": "sent",
                        "attempt_count": attempt_count,
                        "last_attempt_at": now,
                    },
                )
                sent_count += 1
                logger.info("Violation notification sent to %s for week %s", emp_id, week.start)
            else:
                backoff = timedelta(minutes=settings.notification_retry_backoff_minutes)
                await notification_repo.update(
                    notification_id,
                    {
                        "status": "pending_retry",
                        "attempt_count": attempt_count,
                        "last_attempt_at": now,
                        "next_retry_at": now + backoff,
                        "error_summary": "SMTP delivery failed.",
                    },
                )
                logger.warning("Notification delivery failed for %s, scheduled retry.", emp_id)

            details.append(
                {
                    "employee_id": emp_id,
                    "employee_name": emp_name,
                    "employee_email": emp_email,
                    "week": (
                        f"{week.start.isoformat()} to {(week.end - timedelta(days=1)).isoformat()}"
                    ),
                    "days_attended": result.days_attended,
                    "total_hours": result.total_hours,
                    "avg_hours_per_day": result.avg_hours_per_day,
                    "violations": result.violation_reasons,
                    "notification_sent": success,
                }
            )

    # Process pending retries
    retry_count = await _process_retries(
        notification_repo, notification_svc, employee_repo, settings
    )

    summary = {
        "status": "completed",
        "weeks_checked": len(weeks_to_check),
        "employees_checked": len(employees),
        "violations_found": violation_count,
        "notifications_sent": sent_count,
        "notifications_skipped": skipped_count,
        "retries_processed": retry_count,
        "details": details,
    }
    logger.info("Monitoring cycle complete: %s", summary)
    return summary


def _get_completed_weeks(today: date, week_start_day: int, lookback_weeks: int = 4) -> list[Any]:
    """Return completed policy weeks going back `lookback_weeks` from today."""
    from app.services.policy_service import get_week_boundary

    weeks = []
    check_date = today - timedelta(days=7)
    for _ in range(lookback_weeks):
        wb = get_week_boundary(check_date, week_start_day)
        if is_week_complete(wb, today):
            weeks.append(wb)
        check_date -= timedelta(days=7)

    # Deduplicate and sort
    seen = set()
    unique = []
    for w in weeks:
        if w.start not in seen:
            seen.add(w.start)
            unique.append(w)
    return sorted(unique, key=lambda w: w.start)


async def _process_retries(
    notification_repo: NotificationRepository,
    notification_svc: NotificationService,
    employee_repo: EmployeeRepository,
    settings: Any,
) -> int:
    """Process any pending retry notifications."""
    pending = await notification_repo.find_pending_retries()
    count = 0
    for notif in pending:
        emp_id = notif["employee_id"]
        emp = await employee_repo.find_by_id(emp_id)
        if emp is None:
            continue

        attempt_count = notif.get("attempt_count", 0) + 1
        if attempt_count > settings.notification_max_retries + 1:
            await notification_repo.update(notif["notification_id"], {"status": "exhausted"})
            continue

        success = await notification_svc.send_violation_email(
            employee_email=notif["employee_email_snapshot"],
            employee_name=emp.get("name", emp_id),
            employee_id=emp.get("employee_id", emp_id),
            department=emp.get("department", "General"),
            week_start=notif["period_start"],
            week_end=notif["period_end"],
            violations=notif.get("violation_summary", []),
        )

        now = datetime.now(tz=UTC)
        if success:
            await notification_repo.update(
                notif["notification_id"],
                {"status": "sent", "attempt_count": attempt_count, "last_attempt_at": now},
            )
            count += 1
        else:
            backoff = timedelta(minutes=settings.notification_retry_backoff_minutes)
            await notification_repo.update(
                notif["notification_id"],
                {
                    "attempt_count": attempt_count,
                    "last_attempt_at": now,
                    "next_retry_at": now + backoff,
                    "status": "exhausted"
                    if attempt_count >= settings.notification_max_retries + 1
                    else "pending_retry",
                },
            )
    return count
